import os
import sys
import subprocess
import time
import threading
import csv
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import psutil

ROOT = Path(__file__).parent.resolve()
RUST_DIR = ROOT / "rust"
CSHARP_DIR = ROOT / "csharp"
RESULTS_DIR = ROOT / "results"

PORT = 9876
IS_WIN = sys.platform == "win32"

MODES = ["rusttorust", "rusttocsharp", "csharptorust", "csharptocsharp"]
MODE_SHORT = {
    "rusttorust":     "Rust->Rust",
    "rusttocsharp":   "Rust->C#",
    "csharptorust":   "C#->Rust",
    "csharptocsharp": "C#->C#",
}


def build_all():
    os.makedirs(RUST_DIR / "target", exist_ok=True)
    os.makedirs(CSHARP_DIR / "target", exist_ok=True)

    server_rs = str(RUST_DIR / "server.rs")
    client_rs = str(RUST_DIR / "client.rs")
    server_out = str(RUST_DIR / "target" / ("server.exe" if IS_WIN else "server"))
    client_out = str(RUST_DIR / "target" / ("client.exe" if IS_WIN else "client"))

    print("  Building Rust binaries...")
    subprocess.run(
        ["rustc", server_rs, "--edition", "2021", "-o", server_out],
        check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["rustc", client_rs, "--edition", "2021", "-o", client_out],
        check=True, capture_output=True, text=True
    )
    print("  Rust OK")

    dotnet = _dotnet_path()

    print("  Building C# binaries...")
    for name in ("server", "client"):
        proj_dir = CSHARP_DIR / f"build_{name}"
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
        subprocess.run(
            [dotnet, "new", "console", "-n", name, "-o", str(proj_dir), "--force"],
            check=True, capture_output=True, text=True
        )
        dst = proj_dir / "Program.cs"
        dst.write_text((CSHARP_DIR / f"{name}.cs").read_text())
        result = subprocess.run(
            [dotnet, "build", str(proj_dir), "-o", str(CSHARP_DIR / "target")],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  C# {name} build failed:")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
    print("  C# OK")


def _dotnet_path():
    if IS_WIN:
        candidates = ["dotnet", "dotnet.exe"]
    else:
        candidates = [
            os.path.expanduser("~/.dotnet/dotnet"),
            "/usr/share/dotnet/dotnet",
            "/usr/bin/dotnet",
            "dotnet",
        ]
    for c in candidates:
        try:
            subprocess.run([c, "--version"], capture_output=True, check=True)
            return c
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("dotnet SDK not found")


dotnet_path = _dotnet_path()


def _binary_path(lang, name):
    if lang == "rust":
        exe = f"{name}.exe" if IS_WIN else name
        return str(RUST_DIR / "target" / exe)
    else:
        dll = CSHARP_DIR / "target" / f"{name}.dll"
        exe = CSHARP_DIR / "target" / f"{name}.exe"
        if IS_WIN and exe.exists():
            return str(exe)
        return [dotnet_path, str(dll)]


def run_test(mode, interval_ms):
    total_reqs = 1000
    delay_total = interval_ms * total_reqs / 1000
    est_total = delay_total + total_reqs * 0.002
    start_time = datetime.now()
    eta = start_time + timedelta(seconds=est_total)

    short = MODE_SHORT.get(mode, mode)

    print(f"\n{'='*60}")
    print(f"  {short}  |  {total_reqs} x {interval_ms}ms")
    print(f"  Started: {start_time.strftime('%H:%M:%S')}  |  ETA: {eta.strftime('%H:%M:%S')}  ({est_total:.0f}s)")
    print(f"{'='*60}")

    mode_dir = RESULTS_DIR / mode
    mode_dir.mkdir(parents=True, exist_ok=True)

    server_lang = "rust" if mode.startswith("rust") else "csharp"
    client_lang = "rust" if mode.endswith("rust") else "csharp"

    server_cmd = _binary_path(server_lang, "server")
    if isinstance(server_cmd, list):
        server_cmd = server_cmd + [str(PORT)]
    else:
        server_cmd = [server_cmd, str(PORT)]

    client_cmd = _binary_path(client_lang, "client")
    if isinstance(client_cmd, list):
        client_cmd = client_cmd + [f"127.0.0.1:{PORT}", str(interval_ms)]
    else:
        client_cmd = [client_cmd, f"127.0.0.1:{PORT}", str(interval_ms)]

    server_proc = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    ready_line = server_proc.stdout.readline().strip()
    if not ready_line.startswith("READY"):
        print(f"  Server failed: {ready_line}")
        server_proc.kill()
        return

    server_pid = server_proc.pid
    print(f"  Server PID {server_pid}  |  Client starting...")

    try:
        ps_proc = psutil.Process(server_pid)
        ps_proc.cpu_percent()
    except psutil.NoSuchProcess:
        print("  Server died prematurely")
        return

    monitor_data = []
    stop_monitor = threading.Event()

    def monitor():
        start = time.monotonic()
        while not stop_monitor.is_set():
            try:
                cpu = ps_proc.cpu_percent()
                mem = ps_proc.memory_info().rss / (1024 * 1024)
                elapsed = time.monotonic() - start
                monitor_data.append((elapsed, cpu, mem))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(0.1)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    latencies = []
    test_start = time.monotonic()

    client_proc = subprocess.Popen(
        client_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in client_proc.stdout:
        line = line.strip()
        if line.startswith("SEQ:"):
            parts = line.split(":")
            seq = int(parts[1])
            latency_ns = int(parts[2])
            latencies.append((seq, latency_ns))

            if seq % 250 == 0:
                elapsed = time.monotonic() - test_start
                rate = seq / elapsed if elapsed > 0 else 0
                remaining = total_reqs - seq
                eta_remaining = remaining / rate if rate > 0 else 0
                done_pct = seq / total_reqs * 100
                bar_len = 20
                filled = int(bar_len * seq / total_reqs)
                bar = "#" * filled + "." * (bar_len - filled)
                print(f"    [{bar}] {seq:4d}/{total_reqs} ({done_pct:3.0f}%)  "
                      f"~{eta_remaining:.0f}s left  {rate:.0f} req/s", end="\r")
                sys.stdout.flush()

        elif line == "DONE":
            break

    print()
    client_proc.wait()
    test_elapsed = time.monotonic() - test_start
    stop_monitor.set()
    monitor_thread.join(timeout=2)

    server_proc.terminate()
    try:
        server_proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server_proc.kill()

    lat_csv = mode_dir / f"latencies_{interval_ms}ms.csv"
    with open(lat_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "latency_ns", "latency_ms"])
        for seq, lat_ns in latencies:
            w.writerow([seq, lat_ns, round(lat_ns / 1_000_000, 4)])

    res_csv = mode_dir / f"resources_{interval_ms}ms.csv"
    with open(res_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "cpu_percent", "memory_mb"])
        for elapsed, cpu, mem in monitor_data:
            w.writerow([f"{elapsed:.3f}", f"{cpu:.1f}", f"{mem:.2f}"])

    end_time = datetime.now()
    print(f"  Finished: {end_time.strftime('%H:%M:%S')}  ({test_elapsed:.0f}s)")

    if latencies:
        lats_ms = [ns / 1_000_000 for _, ns in latencies]
        lats_ms.sort()
        avg = sum(lats_ms) / len(lats_ms)
        p99 = lats_ms[int(len(lats_ms) * 0.99)]
        p50 = lats_ms[int(len(lats_ms) * 0.50)]
        print(f"  Results: {len(lats_ms)} requests")
        print(f"    Latency  min={min(lats_ms):.4f}ms  avg={avg:.4f}ms  "
              f"p50={p50:.4f}ms  p99={p99:.4f}ms  max={max(lats_ms):.4f}ms")
        if monitor_data:
            peak_cpu = max(m[1] for m in monitor_data)
            avg_cpu = sum(m[1] for m in monitor_data) / len(monitor_data)
            peak_mem = max(m[2] for m in monitor_data)
            avg_mem = sum(m[2] for m in monitor_data) / len(monitor_data)
            print(f"    CPU  peak={peak_cpu:.1f}%  avg={avg_cpu:.1f}%")
            print(f"    RAM  peak={peak_mem:.2f}MB  avg={avg_mem:.2f}MB")

    print(f"  Saved to {mode_dir}/")


def main():
    if len(sys.argv) < 3:
        print(f"\n  TCP Echo Latency Benchmark\n")
        print(f"  Usage: python test.py <mode> <interval_ms>\n")
        print(f"  Modes:")
        for m in MODES:
            print(f"    {m:15s}  {MODE_SHORT[m]}")
        print(f"    all             All 4 combos back-to-back\n")
        print(f"  Examples:")
        print(f"    python test.py rusttorust 100")
        print(f"    python test.py all 50\n")
        sys.exit(1)

    mode = sys.argv[1].lower()
    interval_ms = int(sys.argv[2])

    print("Building all binaries...")
    build_all()
    print("Build complete.\n")

    if mode == "all":
        total_est = 0
        for m in MODES:
            total_est += (1000 * interval_ms / 1000)
        eta = datetime.now() + timedelta(seconds=total_est)
        print(f"  Running all 4 combos x {interval_ms}ms")
        print(f"  Estimated finish ~{eta.strftime('%H:%M:%S')}  ({total_est:.0f}s total)\n")

        for i, m in enumerate(MODES, 1):
            print(f"  [{i}/4] {MODE_SHORT.get(m, m)}")
            run_test(m, interval_ms)
    elif mode in MODES:
        run_test(mode, interval_ms)
    else:
        print(f"\n  Unknown mode: {mode}")
        print(f"  Valid modes: {', '.join(MODES)}, all\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
