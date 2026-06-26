# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv>=1.0.0"]
# ///
"""数据模式检测脚本（首次激活时由模型静默调用）。

只读 .env，不触发任何数据源依赖，因此 PEP723 仅声明 python-dotenv。
输出 JSON，供模型判断是否需要引导用户配置数据模式。

用法：
    uv run scripts/check_mode.py

输出字段：
    mode          当前 DATA_MODE（free / websearch / ""）
    configured    是否已完成有效配置（mode 为 free 或 websearch）
    env_exists    .env 文件是否存在
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import dotenv_values

# 项目根目录：scripts/ 的上一级
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def detect_mode() -> dict[str, object]:
    """读取 .env，返回数据模式配置状态。"""
    env_exists = ENV_PATH.exists()
    values = dotenv_values(ENV_PATH) if env_exists else {}

    mode = (values.get("DATA_MODE") or "").strip()

    # free（免费数据源）/ websearch（纯角色对话）均无需 Token
    configured = mode in ("free", "websearch")

    return {
        "mode": mode,
        "configured": configured,
        "env_exists": env_exists,
    }


def main() -> None:
    print(json.dumps(detect_mode(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
