"""重启后端服务并做健康检查。

Description:
    通过端口定位后端进程，结束它，再用项目 .venv 的解释器重新启动，
    最后访问 /api/v1/health 验证启动成功。

Usage:
    uv run python scripts/restart_backend_v2.py
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


def find_backend_process(port: int = PORT) -> int | None:
    """查找监听指定端口的后端进程。

    Args:
        port: 端口号。

    Returns:
        进程 PID，未找到时返回 None。
    """
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
    for line in result.stdout.splitlines():
        if f"127.0.0.1:{port}" in line or f"0.0.0.0:{port}" in line:
            parts = line.strip().split()
            if len(parts) >= 5:
                return int(parts[-1])
    return None


def main() -> int:
    """执行重启并验证。

    Returns:
        进程退出码。
    """
    pid = find_backend_process()
    if pid:
        print(f"Found backend process PID={pid}, stopping...")
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, timeout=15
        )
        print(f"  taskkill: {r.stdout.strip() or r.stderr.strip()}")
        time.sleep(2)
    else:
        print(f"No backend process found on port {PORT}")

    print("Starting new backend...")
    subprocess.Popen(
        [resolve_python(), "main.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0),
    )
    print(f"Backend started, waiting for init... (cwd={PROJECT_ROOT})")
    time.sleep(5)

    print("Done. Testing...")
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
            print(f"Health: {resp.read().decode()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
