import sys
import subprocess
from datetime import datetime, timedelta

INTERVALS = [1, 2, 50, 100, 250, 500]
MODES = ["rusttorust", "rusttocsharp", "csharptorust", "csharptocsharp"]


def run_mode(mode):
    total_est = sum(1000 * ms / 1000 for ms in INTERVALS)
    eta = datetime.now() + timedelta(seconds=total_est)
    print(f"\n{'='*60}")
    print(f"  Mode: {mode}  |  {len(INTERVALS)} intervals to run")
    print(f"  ETA: {eta.strftime('%H:%M:%S')}  (~{total_est:.0f}s)")
    print(f"{'='*60}")

    for i, ms in enumerate(INTERVALS, 1):
        print(f"\n  [{i}/{len(INTERVALS)}] interval = {ms}ms")
        result = subprocess.run(
            [sys.executable, "test.py", mode, str(ms)]
        )
        if result.returncode != 0:
            print(f"  [!] test.py failed on {mode} {ms}ms (exit code {result.returncode})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python automater.py <mode>")
        print(f"  modes: {', '.join(MODES)}, all")
        print(f"  Intervals: {', '.join(f'{i}ms' for i in INTERVALS)}")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "all":
        total = len(MODES) * len(INTERVALS)
        grand_total = sum(1000 * ms / 1000 for ms in INTERVALS) * len(MODES)
        eta = datetime.now() + timedelta(seconds=grand_total)
        print(f"\n{'='*60}")
        print(f"  Full automation: {len(MODES)} modes x {len(INTERVALS)} intervals = {total} tests")
        print(f"  ETA: {eta.strftime('%H:%M:%S')}  (~{grand_total:.0f}s)")
        print(f"{'='*60}\n")

        for i, m in enumerate(MODES, 1):
            print(f"\n{'='*60}")
            print(f"  [{i}/{len(MODES)}] {m}")
            print(f"{'='*60}")
            run_mode(m)
    elif mode in MODES:
        run_mode(mode)
    else:
        print(f"Unknown mode: {mode}")
        print(f"Valid modes: {', '.join(MODES)}, all")
        sys.exit(1)

    print(f"\n  Done. All results in results/")

if __name__ == "__main__":
    main()
