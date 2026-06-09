"""Dashboard 启动脚本测试。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _load_start_dashboard_module():
    """从脚本路径动态导入模块，避免要求 `scripts/` 成为包。"""
    script_path = PROJECT_ROOT / "scripts" / "start_dashboard.py"
    spec = importlib.util.spec_from_file_location("start_dashboard_script", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load scripts/start_dashboard.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_streamlit_command_uses_dashboard_port_and_current_python() -> None:
    """
    Given:
        当前项目真实的 `config/settings.yaml`，其中包含 `dashboard.port=8501` 配置。

    When:
        动态导入 `scripts/start_dashboard.py` 并调用 `build_streamlit_command()`。

    Then:
        - 命令应使用当前 Python 解释器；
        - 命令主体应为 `-m streamlit run <app.py>`；
        - 端口参数应与 `settings.dashboard.port` 保持一致。
    """
    module = _load_start_dashboard_module()

    command = module.build_streamlit_command()

    assert command[0] == sys.executable
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert command[4].endswith("src\\observability\\dashboard\\app.py")
    assert command[5:8] == ["--server.port", "8501", "--server.headless"]
    assert command[8] == "true"
