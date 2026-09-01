"""Restart the FastAPI backend to pick up auth code changes.

The auth code on disk now returns tenant_id='default', matching the database.
The running process uses old code (tenant_id='dev'), so tasks/assets return 0.
"""

import subprocess
import sys
import os
import time


def find_backend_process():
    """Find the FastAPI backend process on port 8002."""
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True, text=True, timeout=10
    )
    for line in result.stdout.splitlines():
        if "127.0.0.1:8002" in line or "0.0.0.0:8002" in line:
            parts = line.strip().split()
            if len(parts) >= 5:
                return int(parts[-1])
    return None


def main():
    os.chdir(r"d:\ait-code\agent_part")

    pid = find_backend_process()
    if pid:
        print(f"Found backend process PID={pid}, stopping...")
        # Use taskkill via subprocess
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=15
        )
        print(f"  taskkill: {r.stdout.strip() or r.stderr.strip()}")
        time.sleep(2)
    else:
        print("No backend process found on port 8002")

    # Start new backend
    print("Starting new backend...")
    python_exe = r"C:\Users\JT\.conda\envs\cbcf\python.exe"
    subprocess.Popen(
        [python_exe, "main.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        cwd=r"d:\ait-code\agent_part",
    )
    print("Backend started, waiting for init...")
    time.sleep(5)
    print("Done. Testing...")

    # Verify
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8002/api/v1/health", timeout=10)
        print(f"Health: {resp.read().decode()}")
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    main()
