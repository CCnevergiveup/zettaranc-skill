# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dotenv>=1.0.0",
# ]
# ///
"""数据模式配置脚本：写入 .env。

由模型在用户选定数据模式后调用，替代旧 CLI 的 setup 向导。Python 只做配置落地，
引导话术由模型用 Z 哥口吻生成。

用法：
    uv run scripts/setup_mode.py --mode free        # 免费数据源 baostock + AKShare（推荐）
    uv run scripts/setup_mode.py --mode websearch   # 纯角色对话，不走行情接口
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 注入项目根目录，使脚本能 import modules 包
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup(mode: str) -> dict:
    """写入数据模式配置。"""
    from modules.setup_wizard import write_env_file

    env_path = write_env_file(mode=mode)
    return {"success": True, "mode": mode, "env_path": env_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="配置数据模式并写入 .env")
    parser.add_argument("--mode", required=True, choices=["free", "websearch"], help="数据模式")
    args = parser.parse_args()

    try:
        data = setup(args.mode)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
