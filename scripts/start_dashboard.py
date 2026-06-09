"""Dashboard 启动脚本（G1）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import load_settings
from observability.logger import get_logger

LOGGER = get_logger("scripts.start_dashboard")


def build_streamlit_command() -> list[str]:
    """生成启动 Streamlit Dashboard 的命令。

    做什么：
    - 读取 `settings.dashboard` 中的端口与启用开关；
    - 固定使用当前解释器 `sys.executable` 启动 `python -m streamlit`；
    - 返回可直接传给 `subprocess.run()` 的参数列表。

    为什么：
    - 使用当前解释器，能确保启动脚本和 Streamlit 运行在同一个 `.venv` 里；
    - 这比依赖系统 PATH 上的 `streamlit.exe` 更稳，尤其适合 IDE 与多环境并存场景。

    失败路径：
    - 若 `dashboard.enabled=false`，直接抛出可读错误，避免用户误以为脚本没有响应。
    """
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    if not settings.dashboard.enabled:
        raise ValueError("Dashboard is disabled in config/settings.yaml (dashboard.enabled=false)")

    app_path = PROJECT_ROOT / "src" / "observability" / "dashboard" / "app.py"
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(settings.dashboard.port),
        "--server.headless",
        "true",
    ]


def main() -> int:
    """启动 Dashboard 并把子进程退出码透传给调用方。"""
    command = build_streamlit_command()
    LOGGER.info("Starting dashboard: %s", " ".join(command))
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
