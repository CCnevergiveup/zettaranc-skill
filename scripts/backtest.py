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
"""回测脚本：少妇战法 / 多策略融合 / 组合回测，输出 JSON 供模型解读。

由模型在用户问「回测一下 XX」「这个战法历史表现如何」时调用。

用法：
    uv run scripts/backtest.py shaofu 600519.SH --days 250
    uv run scripts/backtest.py multi 600519.SH --days 120
    uv run scripts/backtest.py portfolio 600519.SH,601318.SH --days 120
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _shaofu_to_dict(result: Any) -> dict:
    """ShaofuBacktestResult → 可序列化字典（百分比数值化）。"""
    trades = [
        {
            "entry_date": t.entry_date,
            "entry_price": t.entry_price,
            "exit_date": t.exit_date,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "pnl_pct": round(t.pnl_pct * 100, 2),
            "holding_days": t.holding_days,
        }
        for t in result.trades
    ]
    return {
        "ts_code": result.ts_code,
        "total_trades": result.total_trades,
        "win_count": result.win_count,
        "win_rate": round(result.win_rate, 3),
        "avg_pnl": round(result.avg_pnl * 100, 2),
        "max_win": round(result.max_win * 100, 2),
        "max_loss": round(result.max_loss * 100, 2),
        "profit_factor": round(result.profit_factor, 2),
        "total_return": round(result.total_return * 100, 2),
        "max_drawdown": round(result.max_drawdown * 100, 2),
        "sharpe_ratio": round(result.sharpe_ratio, 2),
        "avg_holding_days": round(result.avg_holding_days, 1),
        "trades": trades,
    }


def _portfolio_to_dict(result: Any) -> dict:
    """PortfolioBacktestResult → 可序列化字典（不含完整资金曲线）。"""
    trades = [
        {
            "ts_code": t.ts_code,
            "entry_date": t.entry_date,
            "entry_price": round(t.entry_price, 2),
            "exit_date": t.exit_date,
            "exit_price": round(t.exit_price, 2) if t.exit_price else None,
            "exit_reason": t.exit_reason,
            "pnl_pct": round(t.pnl_pct * 100, 2),
        }
        for t in result.trades
    ]
    return {
        "initial_capital": result.initial_capital,
        "final_value": round(result.final_value, 2),
        "total_return": round(result.total_return * 100, 2),
        "annualized_return": round(result.annualized_return * 100, 2),
        "sharpe_ratio": round(result.sharpe_ratio, 2),
        "max_drawdown": round(result.max_drawdown * 100, 2),
        "win_rate": round(result.win_rate, 3),
        "profit_factor": round(result.profit_factor, 2),
        "total_trades": result.total_trades,
        "trades": trades,
    }


def _shaofu_portfolio_to_dict(result: dict) -> dict:
    """backtest_shaofu_portfolio 的 dict 结果 → 摘要。"""
    return {
        "per_stock": [_shaofu_to_dict(r) for r in result.get("results", [])],
        "total_return": round(result.get("total_return", 0) * 100, 2),
        "total_trades": result.get("total_trades", 0),
        "overall_win_rate": round(result.get("overall_win_rate", 0), 3),
        "max_drawdown": round(result.get("max_drawdown", 0) * 100, 2),
        "sharpe_ratio": round(result.get("sharpe_ratio", 0), 2),
    }


def run_backtest(mode: str, ts_code: str | None, codes: str | None, days: int) -> dict:
    """按模式分派回测。"""
    if mode == "shaofu":
        from modules.backtest_six_step import backtest_shaofu_single

        return _shaofu_to_dict(backtest_shaofu_single(ts_code, days=days))

    if mode == "multi":
        from modules.backtest import backtest_multi_strategy

        return _portfolio_to_dict(backtest_multi_strategy(ts_code, days=days))

    # portfolio
    ts_codes = [c.strip() for c in (codes or "").split(",") if c.strip()]
    if not ts_codes:
        raise ValueError("组合回测需要逗号分隔的股票代码")
    if len(ts_codes) == 1:
        from modules.backtest_six_step import backtest_shaofu_single

        return _shaofu_to_dict(backtest_shaofu_single(ts_codes[0], days=days))
    from modules.backtest_six_step import backtest_shaofu_portfolio

    return _shaofu_portfolio_to_dict(backtest_shaofu_portfolio(ts_codes, days=days))


def main() -> None:
    parser = argparse.ArgumentParser(description="策略回测（shaofu / multi / portfolio）")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_shaofu = sub.add_parser("shaofu", help="少妇战法六步回测")
    p_shaofu.add_argument("ts_code", help="股票代码")
    p_shaofu.add_argument("--days", type=int, default=250, help="回测天数（默认 250）")

    p_multi = sub.add_parser("multi", help="多策略融合回测")
    p_multi.add_argument("ts_code", help="股票代码")
    p_multi.add_argument("--days", type=int, default=120, help="回测天数（默认 120）")

    p_portfolio = sub.add_parser("portfolio", help="多股票组合回测")
    p_portfolio.add_argument("codes", help="股票代码，逗号分隔")
    p_portfolio.add_argument("--days", type=int, default=120, help="回测天数（默认 120）")

    args = parser.parse_args()

    try:
        data = run_backtest(
            args.mode,
            getattr(args, "ts_code", None),
            getattr(args, "codes", None),
            args.days,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc), "mode": args.mode}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
