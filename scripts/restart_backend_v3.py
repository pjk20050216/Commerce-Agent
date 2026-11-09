"""强制重启后端服务（清理端口占用后启动）。

Description:
    结束所有监听 8002 端口的进程，确认端口释放后，
    用项目 .venv 的解释器重新启动后端，并验证健康状态。

Usage:
    uv run python scripts/restart_backend_v3.py
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT = 8002
HEALTH_URL = f"http://localhost:{PORT}/api/v1/health"


def resolve_python() -> str:
    """解析项目解释器路径。

    Returns:
        优先返回 .venv 中的 python，不存在时回退到当前解释器。
    """
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def find_backend_processes(port: int = PORT) -> list[int]:
    """查找所有监听指定端口的进程。

    Args:
        port: 端口号。

    Returns:
        去重并排序后的 PID 列表。
    """
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = line.strip().split()
            if len(parts) >= 5:
                pids.add(int(parts[-1]))
    return sorted(pids)


def main() -> int:
    """执行强制重启并验证。

    Returns:
        进程退出码。
    """
    pids = find_backend_processes()
    print(f"Found PIDs on port {PORT}: {pids}")

    for pid in pids:
        print(f"Killing PID {pid}...")
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, timeout=15
        )
        print(f"  {r.stdout.strip() or r.stderr.strip()}")

    # 检查是否仍有本项目遗留的 python 进程占用
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in result.stdout.splitlines():
        if "main.py" in line:
            print(f"Still holding main.py: {line.strip()}")

    time.sleep(2)

    remaining = find_backend_processes()
    if remaining:
        print(f"WARNING: PIDs still on port {PORT}: {remaining}")
    else:
        print(f"Port {PORT} is free")

    print("\nStarting new backend...")
    subprocess.Popen(
        [resolve_python(), "main.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0),
    )
    print(f"Backend started, waiting 8s for init... (cwd={PROJECT_ROOT})")
    time.sleep(8)

    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
            print(f"Health: {resp.read().decode()}")
    except Exception as e:
        print(f"Health check failed: {e}")

    print(f"PIDs on port {PORT} after restart: {find_backend_processes()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
