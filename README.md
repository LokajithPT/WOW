# TCP Echo Latency Benchmark

Measures round-trip latency and server resource usage across 4 Rust/C# combinations.

## Project Structure

```
.
├── rust/
│   ├── server.rs          # Rust TCP echo server
│   ├── client.rs          # Rust TCP echo client
│   └── target/            # compiled binaries (auto-created)
├── csharp/
│   ├── server.cs          # C# TCP echo server
│   ├── client.cs          # C# TCP echo client
│   └── target/            # compiled DLLs (auto-created)
├── test.py                # benchmark orchestrator
├── plot.py                # results visualizer
└── results/               # output directory (auto-created)
    ├── rusttorust/
    ├── rusttocsharp/
    ├── csharptorust/
    └── csharptocsharp/
```

## Prerequisites

| Tool | Linux | Windows |
|---|---|---|
| **Rust** | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` | [rustup.rs](https://rustup.rs) installer |
| **.NET SDK 10+** | [dotnet.microsoft.com](https://dotnet.microsoft.com/en-us/download) | [dotnet.microsoft.com](https://dotnet.microsoft.com/en-us/download) |
| **Python 3.10+** | `apt install python3` / `pacman -S python` | [python.org](https://python.org) |
| **psutil** | `pip install psutil --break-system-packages` | `pip install psutil` |
| **matplotlib** | `pip install matplotlib --break-system-packages` | `pip install matplotlib` |
| **pandas** | `pip install pandas --break-system-packages` | `pip install pandas` |

> On Linux you may need `--break-system-packages` if Python packages are managed by the system package manager.
> On Windows use **Command Prompt** or **PowerShell** — avoid WSL for consistent timing.

## How to Run

### 1. Build + run a single test

```bash
# Rust server + Rust client, 100ms between each request
python test.py rusttorust 100

# Rust server + C# client
python test.py rusttocsharp 50

# C# server + Rust client
python test.py csharptorust 200

# C# server + C# client
python test.py csharptocsharp 500
```

### 2. Run all 4 combos back-to-back

```bash
python test.py all 100
```

Each combo sends **1000 requests** and logs latency + CPU + RAM every 100ms.

### 3. Generate plots

```bash
python plot.py
```

Creates 3 PNGs per combo per interval inside each `results/<mode>/` folder:

| File | Shows |
|---|---|
| `latency_<interval>ms.png` | Request-by-request latency with rolling avg + stats |
| `cpu_<interval>ms.png` | Server CPU % over time |
| `ram_<interval>ms.png` | Server memory (MB) over time |

### 4. View results

```bash
ls results/rusttorust/
# latencies_100ms.csv  resources_100ms.csv  latency_100ms.png  cpu_100ms.png  ram_100ms.png
```

## What Each Test Does

1. Server listens on `127.0.0.1:9876`, accepts one connection
2. Client connects and sends `<seq>:<seq>\n` 1000 times
3. Server replies `ACK:<seq>\n` immediately
4. Client waits `interval_ms` between each request
5. test.py samples server CPU/RAM every 100ms
6. All data saved as CSVs for custom analysis

## CSV Formats

**`latencies_<interval>ms.csv`**

```csv
seq,latency_ns,latency_ms
1,133457,0.1335
2,88822,0.0888
```

**`resources_<interval>ms.csv`**

```csv
elapsed_s,cpu_percent,memory_mb
0.000,0.0,2.14
0.101,0.0,2.15
```

## Notes

- Uses `TCP_NODELAY` on all sockets (Nagle's algorithm disabled)
- Latency measured client-side with monotonic clocks
- CPU measured via `psutil.Process.cpu_percent()` (non-blocking)
- All 4 combos can run side-by-side with `all` mode
