"""重启后端服务（最简版本）。

Description:
    结束所有无窗口的 python 进程，然后用项目 .venv 的解释器重新启动 main.py。
    项目根目录与解释器均由脚本位置推导，不依赖任何绝对路径。

Usage:
    uv run python scripts/restart_backend.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_python() -> str:
    """解析项目解释器路径。

    Returns:
        优先返回 .venv 中的 python，不存在时回退到当前解释器。
    """
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def main() -> int:
    """执行重启。

    Returns:
        进程退出码。
    """
    # 结束无窗口的 python 进程
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-Process python -ErrorAction SilentlyContinue "
            '| Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force',
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print("Killed result:", result.returncode)

    # 启动新后端
    subprocess.Popen(
        [resolve_python(), "main.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0),
    )
    print(f"New process started (cwd={PROJECT_ROOT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
