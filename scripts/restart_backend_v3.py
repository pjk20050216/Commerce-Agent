"""Kill ALL backend processes on port 8002 and start fresh."""
import subprocess
import sys
import os
import time


def find_backend_processes(port=8002):
    """Find ALL processes listening on the given port."""
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True, text=True, timeout=10
    )
    pids = set()
    for line in result.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = line.strip().split()
            if len(parts) >= 5:
                pids.add(int(parts[-1]))
    return sorted(pids)


def main():
    os.chdir(r"d:\ait-code\agent_part")

    # Find and kill ALL processes on port 8002
    pids = find_backend_processes(8002)
    print(f"Found PIDs on port 8002: {pids}")

    for pid in pids:
        print(f"Killing PID {pid}...")
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=15
        )
        print(f"  {r.stdout.strip() or r.stderr.strip()}")

    # Also kill any cbcf python processes that might be holding the port
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
        capture_output=True, text=True, timeout=10
    )
    for line in result.stdout.splitlines():
        if "main.py" in line or "cbcf" in line:
            print(f"Found cbcf python: {line}")

    time.sleep(2)

    # Verify port is free
    remaining = find_backend_processes(8002)
    if remaining:
        print(f"WARNING: PIDs still on port 8002: {remaining}")
    else:
        print("Port 8002 is free")

    # Start new backend
    print("\nStarting new backend...")
    python_exe = r"C:\Users\JT\.conda\envs\cbcf\python.exe"
    subprocess.Popen(
        [python_exe, "main.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        cwd=r"d:\ait-code\agent_part",
    )
    print("Backend started, waiting 8s for init...")
    time.sleep(8)

    # Verify
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8002/api/v1/health", timeout=10)
        print(f"Health: {resp.read().decode()}")
    except Exception as e:
        print(f"Health check failed: {e}")

    # Check which PIDs are now on port 8002
    new_pids = find_backend_processes(8002)
    print(f"PIDs on port 8002 after restart: {new_pids}")


if __name__ == "__main__":
    main()
