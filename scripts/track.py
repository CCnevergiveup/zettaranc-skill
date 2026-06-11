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
"""跟踪池脚本（自我改进系统·数据采集层）。

由模型在用户说「把这几只票加进跟踪」「看看我的跟踪池」「同步跟踪数据」时调用。
负责跟踪池的增删查改，以及把 K 线/指标/信号同步进 tracking_records_self 表，
为月度复盘（review.py）积累真实数据。

用法：
    uv run scripts/track.py add 600519.SH --reason "B1买点" --strategy B1
    uv run scripts/track.py remove 600519.SH --reason "已卖出"
    uv run scripts/track.py list
    uv run scripts/track.py info 600519.SH
    uv run scripts/track.py status 600519.SH --set paused
    uv run scripts/track.py stats
    uv run scripts/track.py sync 600519.SH
    uv run scripts/track.py sync --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def ensure_tables() -> None:
    """确保 4 张 _self 表存在（init_database 不建它们，需显式执行 SQL）。"""
    from modules.database import get_connection

    sql_path = PROJECT_ROOT / "modules" / "tracking_tables.sql"
    sql = sql_path.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(sql)
        conn.commit()


def cmd_add(args) -> dict:
    """添加股票到跟踪池。"""
    from modules.tracking_manager import TrackingManager

    ok = TrackingManager().add_stock(
        ts_code=args.ts_code,
        name=args.name,
        reason=args.reason,
        strategy_tags=args.strategy,
        notes=args.notes,
    )
    return {"success": ok, "ts_code": args.ts_code}


def cmd_remove(args) -> dict:
    """从跟踪池移除股票。"""
    from modules.tracking_manager import TrackingManager

    ok = TrackingManager().remove_stock(ts_code=args.ts_code, reason=args.reason)
    return {"success": ok, "ts_code": args.ts_code}


def cmd_list(args) -> dict:
    """列出跟踪池股票。"""
    from modules.tracking_manager import TrackingManager

    tag = args.strategy[0] if args.strategy else None
    stocks = TrackingManager().list_stocks(status=args.status, strategy_tag=tag)
    return {"status": args.status, "count": len(stocks), "stocks": stocks}


def cmd_info(args) -> dict:
    """查看单只股票跟踪详情。"""
    from modules.tracking_manager import TrackingManager

    return {"stock": TrackingManager().get_stock_info(args.ts_code)}


def cmd_status(args) -> dict:
    """更新股票跟踪状态。"""
    from modules.tracking_manager import TrackingManager

    ok = TrackingManager().update_stock_status(ts_code=args.ts_code, status=args.set, notes=args.notes)
    return {"success": ok, "ts_code": args.ts_code, "status": args.set}


def cmd_stats(args) -> dict:
    """跟踪池统计 + 策略分布。"""
    from modules.tracking_manager import TrackingManager

    manager = TrackingManager()
    return {"stats": manager.get_tracking_stats(), "distribution": manager.get_strategy_distribution()}


def cmd_sync(args) -> dict:
    """同步跟踪股票的 K 线/指标/信号到记录表。"""
    from modules.tracking_syncer import TrackingSyncer

    syncer = TrackingSyncer()
    if args.all:
        return syncer.sync_all_active(days=args.days)
    if not args.ts_code:
        return {"success": False, "error": "请指定股票代码或 --all"}
    return syncer.sync_daily(args.ts_code, days=args.days)


def main() -> None:
    parser = argparse.ArgumentParser(description="跟踪池管理（自我改进系统·数据采集层）")
    sub = parser.add_subparsers(dest="action", required=True)

    p_add = sub.add_parser("add", help="添加股票到跟踪池")
    p_add.add_argument("ts_code", help="股票代码")
    p_add.add_argument("--name", help="股票名称")
    p_add.add_argument("--reason", help="跟踪原因")
    p_add.add_argument("--strategy", nargs="+", help="策略标签（可多个）")
    p_add.add_argument("--notes", help="备注")

    p_rm = sub.add_parser("remove", help="从跟踪池移除")
    p_rm.add_argument("ts_code", help="股票代码")
    p_rm.add_argument("--reason", help="移除原因")

    p_list = sub.add_parser("list", help="列出跟踪池股票")
    p_list.add_argument("--status", default="active", help="状态筛选（active/paused/removed）")
    p_list.add_argument("--strategy", nargs="+", help="策略标签筛选")

    p_info = sub.add_parser("info", help="查看单只股票详情")
    p_info.add_argument("ts_code", help="股票代码")

    p_st = sub.add_parser("status", help="更新跟踪状态")
    p_st.add_argument("ts_code", help="股票代码")
    p_st.add_argument("--set", required=True, choices=["active", "paused", "removed"], help="目标状态")
    p_st.add_argument("--notes", help="备注")

    sub.add_parser("stats", help="跟踪池统计")

    p_sync = sub.add_parser("sync", help="同步跟踪数据")
    p_sync.add_argument("ts_code", nargs="?", help="股票代码（不传需 --all）")
    p_sync.add_argument("--all", action="store_true", help="同步所有活跃股票")
    p_sync.add_argument("--days", type=int, default=365, help="同步天数（默认 365）")

    args = parser.parse_args()

    handlers = {
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "info": cmd_info,
        "status": cmd_status,
        "stats": cmd_stats,
        "sync": cmd_sync,
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
