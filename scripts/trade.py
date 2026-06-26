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
"""交易记录脚本：解析并保存交易、列出记录、构建复盘上下文。

由模型在用户说「我今天买了 XX」「看看我的交易记录」「复盘一下」时调用。
Python 只做解析 + 数据准备；review 子命令输出的 prompt 供模型用 Z 哥口吻点评。

用法：
    uv run scripts/trade.py add "4月25号买了100股茅台，1800块"
    uv run scripts/trade.py list
    uv run scripts/trade.py review
    uv run scripts/trade.py stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_add(text: str) -> dict:
    """解析口语化交易描述并保存到数据库。"""
    from modules.trade_parser import TradeParser
    from modules.trade_manager import TradeManager

    parser = TradeParser()
    result = parser.parse(text)
    if not result.success:
        return {"success": False, "error": result.error_message}

    data = result.data or {}
    required = ["ts_code", "action", "price", "quantity"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {
            "success": False,
            "parsed": data,
            "confidence": result.confidence,
            "missing_fields": missing,
            "error": f"缺少必填字段: {missing}",
        }

    if "amount" not in data and data.get("price") and data.get("quantity"):
        data["amount"] = round(float(data["price"]) * int(data["quantity"]), 2)

    trade_id = TradeManager().add_trade(data)
    return {"success": True, "trade_id": trade_id, "parsed": data, "confidence": result.confidence}


def cmd_list(limit: int) -> dict:
    """列出最近交易记录。"""
    from modules.trade_manager import TradeManager

    return {"trades": TradeManager().get_recent_trades(limit=limit)}


def cmd_review() -> dict:
    """构建最近一笔交易的复盘上下文（含给模型的点评 prompt）。"""
    from modules.trade_manager import TradeManager
    from modules.trade_reviewer import TradeReviewer

    trades = TradeManager().get_recent_trades(limit=1)
    if not trades:
        return {"success": False, "error": "暂无交易记录"}

    reviewer = TradeReviewer()
    ctx = reviewer.prepare_review_context(trades[0])
    ctx = reviewer.enrich_with_indicators(ctx)
    if ctx.action == "SELL":
        ctx = reviewer.enrich_with_buy_info(ctx)
    ctx = reviewer.check_if_complete_trade(ctx)

    return {
        "success": True,
        "ts_code": ctx.ts_code,
        "name": ctx.name,
        "trade_date": ctx.trade_date,
        "action": ctx.action,
        "price": ctx.price,
        "quantity": ctx.quantity,
        "amount": ctx.amount,
        "reason": ctx.reason,
        "avg_cost": ctx.avg_cost,
        "profit_pct": ctx.profit_pct,
        "holding_days": ctx.holding_days,
        "signal_type": ctx.signal_type,
        "is_complete_trade": ctx.is_complete_trade,
        "indicators": ctx.indicators,
        "review_prompt": ctx.get_full_prompt(),
    }


def cmd_stats() -> dict:
    """交易统计摘要 + 盈亏。"""
    from modules.trade_manager import TradeManager

    manager = TradeManager()
    return {"summary": manager.get_summary(), "pnl": manager.calculate_pnl()}


def main() -> None:
    parser = argparse.ArgumentParser(description="交易记录管理（add / list / review / stats）")
    sub = parser.add_subparsers(dest="action", required=True)

    p_add = sub.add_parser("add", help="解析并保存交易")
    p_add.add_argument("text", help="口语化交易描述")

    p_list = sub.add_parser("list", help="列出最近交易")
    p_list.add_argument("--limit", type=int, default=20, help="条数（默认 20）")

    sub.add_parser("review", help="构建最近一笔交易的复盘上下文")
    sub.add_parser("stats", help="交易统计摘要")

    args = parser.parse_args()

    try:
        if args.action == "add":
            data = cmd_add(args.text)
        elif args.action == "list":
            data = cmd_list(args.limit)
        elif args.action == "review":
            data = cmd_review()
        else:
            data = cmd_stats()
    except Exception as exc:
        print(json.dumps({"error": str(exc), "action": args.action}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
