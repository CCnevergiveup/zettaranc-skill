# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tushare>=1.4.0",
#     "python-dotenv>=1.0.0",
#     "pandas>=2.0.0",
#     "requests>=2.28.0",
# ]
# ///
"""数据模式配置脚本：写入 .env，可选测试 Tushare 连通性。

由模型在用户选定数据模式后调用，替代旧 CLI 的 setup 向导。Python 只做配置落地，
引导话术由模型用 Z 哥口吻生成。

用法：
    uv run scripts/setup_mode.py --mode websearch
    uv run scripts/setup_mode.py --mode free
    uv run scripts/setup_mode.py --mode jnb --token <56位Token>
    uv run scripts/setup_mode.py --mode jnb --token <Token> --test   # 写入前先测连通性
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 注入项目根目录，使脚本能 import modules 包
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup(mode: str, token: str | None, do_test: bool) -> dict:
    """写入数据模式配置，jnb 模式可选先测连通性。"""
    from modules.setup_wizard import write_env_file, test_jnb_connection

    # jnb 模式且要求测试：先验证 Token 再写入
    if mode == "jnb" and do_test:
        if not token:
            return {"success": False, "error": "jnb 模式需要 --token"}
        if not test_jnb_connection(token):
            return {"success": False, "error": "Tushare 连通性测试失败，请检查 Token 或中转 API"}

    env_path = write_env_file(token=token, mode=mode)
    return {"success": True, "mode": mode, "env_path": env_path, "token_set": bool(token)}


def main() -> None:
    parser = argparse.ArgumentParser(description="配置数据模式并写入 .env")
    parser.add_argument("--mode", required=True, choices=["free", "jnb", "websearch"], help="数据模式")
    parser.add_argument("--token", help="Tushare Token（jnb 模式用）")
    parser.add_argument("--test", action="store_true", help="jnb 模式写入前先测连通性")
    args = parser.parse_args()

    try:
        data = setup(args.mode, args.token, args.test)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
