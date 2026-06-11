# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tushare>=1.4.0",
#     "python-dotenv>=1.0.0",
#     "pandas>=2.0.0",
#     "requests>=2.28.0",
#     "baostock>=0.9.1",
#     "akshare>=1.18.64",
# ]
# ///
"""持仓诊断脚本：防卖飞评分 + 出货信号扫描 + 风险评级。

由模型在用户问「帮我诊断一下 XX」「我持有的 XX 现在怎么样」时调用，
输出 JSON 供模型用 Z 哥口吻包装。

用法：
    uv run scripts/diagnose.py 600519.SH
    uv run scripts/diagnose.py 600519.SH --days 120
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def diagnose(ts_code: str, days: int) -> dict:
    """复用 portfolio_diagnosis.diagnose_stock 完成持仓诊断。"""
    from modules.portfolio_diagnosis import diagnose_stock

    result = diagnose_stock(ts_code, days=days)
    return asdict(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="持仓诊断（防卖飞 + 出货信号）")
    parser.add_argument("ts_code", help="股票代码，如 600519.SH")
    parser.add_argument("--days", type=int, default=120, help="分析天数（默认 120）")
    args = parser.parse_args()

    try:
        data = diagnose(args.ts_code, args.days)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "ts_code": args.ts_code}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
