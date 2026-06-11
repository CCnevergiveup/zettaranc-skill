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
"""复盘脚本（自我改进系统·分析与建议层）。

由模型在用户说「复盘下这个月」「跟踪池表现怎么样」「该优化哪些策略」时调用。
基于 track.py 积累的真实跟踪数据，产出月度复盘、策略表现分析和改进建议。

重要：本脚本只产出"建议"（JSON），不改任何文件。模型读到建议后，应向用户
提议是否将结论落地到 SKILL.md / knowledge，经用户确认后再用 Edit 修改。

用法：
    uv run scripts/review.py monthly 2026-05          # 生成并保存月度复盘
    uv run scripts/review.py monthly 2026-05 --no-save # 只生成不入库
    uv run scripts/review.py strategy 2026-05         # 策略表现 + Guardrails 建议
    uv run scripts/review.py history                  # 历史复盘月份列表
    uv run scripts/review.py suggest                  # 基于日志的优化建议
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def ensure_tables() -> None:
    """确保 4 张 _self 表存在。"""
    from modules.database import get_connection

    sql = (PROJECT_ROOT / "modules" / "tracking_tables.sql").read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(sql)
        conn.commit()


def cmd_monthly(args) -> dict:
    """生成月度复盘报告，默认入库（每只股票一条）。"""
    from modules.review_generator import ReviewGenerator

    gen = ReviewGenerator()
    result = gen.generate_monthly_review(args.month)

    # 默认把每只股票的复盘结果落库，供 strategy 分析使用
    if result.get("success") and not args.no_save:
        for review in result.get("reviews", []):
            gen.save_review_to_database(review)
        for perf in result.get("strategy_stats", []):
            gen.save_strategy_performance(perf)

    return result


def cmd_strategy(args) -> dict:
    """分析策略表现，产出 Guardrails 更新建议（只建议，不落地）。"""
    from modules.harness_updater import HarnessUpdater

    updater = HarnessUpdater()
    analysis = updater.analyze_strategy_performance(args.month)
    if not analysis.get("success"):
        return analysis
    updates = updater.generate_guardrails_update(analysis)
    return {"analysis": analysis, "guardrails_suggestions": updates}


def cmd_history(args) -> dict:
    """历史复盘月份列表。"""
    from modules.review_generator import ReviewGenerator

    return {"history": ReviewGenerator().get_historical_reviews(limit=args.limit)}


def cmd_suggest(args) -> dict:
    """基于改进日志的优化建议。"""
    from modules.log_analyzer import LogAnalyzer

    return LogAnalyzer().generate_optimization_report()


def main() -> None:
    parser = argparse.ArgumentParser(description="复盘与改进建议（自我改进系统·分析层）")
    sub = parser.add_subparsers(dest="action", required=True)

    p_m = sub.add_parser("monthly", help="生成月度复盘报告")
    p_m.add_argument("month", help="复盘月份，格式 YYYY-MM")
    p_m.add_argument("--no-save", action="store_true", help="只生成不入库")

    p_s = sub.add_parser("strategy", help="策略表现 + Guardrails 建议")
    p_s.add_argument("month", nargs="?", help="复盘月份（不传取最新）")

    p_h = sub.add_parser("history", help="历史复盘月份列表")
    p_h.add_argument("--limit", type=int, default=12, help="返回数量（默认 12）")

    sub.add_parser("suggest", help="基于日志的优化建议")

    args = parser.parse_args()

    handlers = {
        "monthly": cmd_monthly,
        "strategy": cmd_strategy,
        "history": cmd_history,
        "suggest": cmd_suggest,
    }

    try:
        ensure_tables()
        data = handlers[args.action](args)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "action": args.action}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
