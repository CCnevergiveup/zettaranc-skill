# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dotenv>=1.0.0",
#     "pandas>=2.0.0",
#     "requests>=2.28.0",
#     "baostock>=0.9.1",
#     "akshare>=1.18.64",
# ]
# ///
"""选股扫描脚本：按战法策略筛选全市场标的，按评分排序。

由模型在用户问「现在能买什么」「选股」时调用，输出 JSON 供模型用 Z 哥口吻包装。

用法：
    uv run scripts/screen.py --strategy B1 --limit 10
    uv run scripts/screen.py --strategy 长安战法 --limit 20

策略别名：B1 B2 B3 超级B1 长安战法 完美图形 建仓波 吸筹 安全 超跌 突破
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CLI 中文别名 → screener 英文 criteria
STRATEGY_ALIAS = {
    "B1": "b1",
    "B2": "b2_breakout",
    "B3": "b3_consensus",
    "完美图形": "perfect",
    "超级B1": "super_b1",
    "长安战法": "changan",
    "建仓波": "build_wave",
    "吸筹": "xishou",
    "安全": "safe",
    "超跌": "oversold",
    "突破": "breakout",
}


def screen(strategy: str, limit: int, no_parallel: bool) -> dict:
    """复用 screener.screen_stocks 完成全市场扫描。"""
    from modules.screener import screen_stocks

    criteria = STRATEGY_ALIAS.get(strategy, strategy)
    results = screen_stocks(
        criteria=criteria,
        max_stocks=limit if limit > 0 else 0,
        use_parallel=not no_parallel,
    )
    output_limit = limit if limit > 0 else len(results)

    return {
        "strategy": strategy,
        "criteria": criteria,
        "count": len(results[:output_limit]),
        "stocks": [
            {
                "ts_code": r.ts_code,
                "name": r.name,
                "score": r.score,
                "rating": r.rating,
                "reasons": getattr(r, "reasons", []) or [],
                "warnings": getattr(r, "warnings", []) or [],
            }
            for r in results[:output_limit]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="选股扫描（11 种战法策略）")
    parser.add_argument("--strategy", default="B1", choices=list(STRATEGY_ALIAS.keys()), help="筛选策略")
    parser.add_argument("--limit", type=int, default=20, help="输出数量（0=全市场 500 上限）")
    parser.add_argument("--no-parallel", action="store_true", help="禁用多进程并行")
    args = parser.parse_args()

    try:
        data = screen(args.strategy, args.limit, args.no_parallel)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "strategy": args.strategy}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
