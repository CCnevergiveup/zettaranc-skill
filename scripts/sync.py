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
"""数据同步脚本：初始化数据库 / 同步 K 线 + 指标缓存 / 查看同步状态。

由模型在需要真实行情但本地无数据时调用（如 analyze 报「数据不足」），
或用户主动要求同步时调用。

用法：
    uv run scripts/sync.py init                          # 初始化数据库（建表）
    uv run scripts/sync.py sync 600519.SH                # 同步单只 K 线 + 指标
    uv run scripts/sync.py sync 600519.SH --days 250     # 指定天数
    uv run scripts/sync.py sync                          # 全市场批量同步
    uv run scripts/sync.py status                        # 查看同步状态
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 取消代理，避免数据源连接问题（仅脚本直调时设置）
os.environ.setdefault("HTTP_PROXY", "")
os.environ.setdefault("HTTPS_PROXY", "")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_init() -> dict:
    """初始化数据库（主系统 10 张表 + 自我改进 4 张 _self 表）。"""
    from modules.database import init_database, get_db_path, get_connection

    init_database()

    # 额外执行 tracking_tables.sql 建 _self 表（init_database 不含这些表）
    sql_path = PROJECT_ROOT / "modules" / "tracking_tables.sql"
    tracking_tables_created = False
    if sql_path.exists():
        with get_connection() as conn:
            conn.executescript(sql_path.read_text(encoding="utf-8"))
            conn.commit()
        tracking_tables_created = True

    return {
        "action": "init",
        "db_path": str(get_db_path()),
        "tracking_tables_created": tracking_tables_created,
    }


def cmd_sync(ts_code: str | None, days: int, skip_indicators: bool, indicators: bool) -> dict:
    """同步 K 线（单只默认带指标缓存，批量需 --indicators）。"""
    from modules.data_sync import DataSyncer

    syncer = DataSyncer()
    if ts_code:
        syncer.sync_daily_kline(ts_code)
        if not skip_indicators:
            syncer.sync_indicator_cache(ts_code, days=days)
    else:
        syncer.sync_stock_basic()
        syncer.sync_all_daily_kline(days=days)
        if indicators and not skip_indicators:
            syncer.sync_all_indicators()

    return {"action": "sync", "ts_code": ts_code or "ALL", "status": syncer.get_sync_status()}


def cmd_status() -> dict:
    """查看同步状态。"""
    from modules.data_sync import DataSyncer

    return {"action": "status", "status": DataSyncer().get_sync_status()}


def main() -> None:
    parser = argparse.ArgumentParser(description="数据同步（init / sync / status）")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("init", help="初始化数据库")

    p_sync = sub.add_parser("sync", help="同步 K 线 + 指标缓存")
    p_sync.add_argument("ts_code", nargs="?", help="股票代码（不传 = 全市场批量）")
    p_sync.add_argument("--days", type=int, default=730, help="同步天数（默认 730）")
    p_sync.add_argument("--indicators", action="store_true", help="批量同步后计算指标缓存")
    p_sync.add_argument("--skip-indicators", action="store_true", help="跳过指标缓存")

    sub.add_parser("status", help="查看同步状态")

    args = parser.parse_args()

    try:
        if args.action == "init":
            data = cmd_init()
        elif args.action == "sync":
            data = cmd_sync(args.ts_code, args.days, args.skip_indicators, args.indicators)
        else:
            data = cmd_status()
    except Exception as exc:
        print(json.dumps({"error": str(exc), "action": args.action}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
