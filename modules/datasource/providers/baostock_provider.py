"""baostock 免费数据源 provider（前复权 K 线 / 基本信息 / 可选估值）。"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from modules.datasource.codecs import (
    baostock_code_to_ts_code,
    infer_market_from_ts_code,
    safe_float,
    ts_code_to_baostock,
)
from modules.datasource.errors import ProviderError
from modules.datasource.models import (
    DAILY_BASIC_COLUMNS,
    DAILY_KLINE_COLUMNS,
    STOCK_BASIC_COLUMNS,
)

# baostock 全局 socket 无内部锁，所有查询串行化
_BS_LOCK = threading.Lock()

# baostock volume 单位为股，本项目 daily_kline.vol 单位为手（1 手 = 100 股）
_VOL_DIVISOR = 100.0
# baostock amount 单位为元，本项目 daily_kline.amount 单位为千元
_AMOUNT_DIVISOR = 1000.0


class BaostockProvider:
    """baostock 数据源 provider。"""

    name = "baostock"

    def __init__(self, max_workers: int = 1) -> None:
        self.max_workers = max_workers

    # ==================== K 线 ====================

    def daily_kline(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """前复权日线（adjustflag=2），映射为 daily_kline 表兼容字段。"""
        bs = self._import_baostock()
        bs_code = ts_code_to_baostock(ts_code)
        rows = self._query_kline(bs, bs_code, start_date, end_date)
        if not rows:
            return pd.DataFrame(columns=DAILY_KLINE_COLUMNS)

        records: list[dict[str, Any]] = []
        prev_close = 0.0
        for date_str, o, h, low, c, vol, amt, pct in rows:
            close = safe_float(c, default=0.0) or 0.0
            pct_chg = safe_float(pct, default=None)
            if pct_chg is None and prev_close > 0:
                pct_chg = (close - prev_close) / prev_close * 100
            records.append(
                {
                    "ts_code": ts_code,
                    "trade_date": str(date_str).replace("-", ""),
                    "open": safe_float(o, default=0.0) or 0.0,
                    "high": safe_float(h, default=0.0) or 0.0,
                    "low": safe_float(low, default=0.0) or 0.0,
                    "close": close,
                    "vol": (safe_float(vol, default=0.0) or 0.0) / _VOL_DIVISOR,
                    "amount": (safe_float(amt, default=0.0) or 0.0) / _AMOUNT_DIVISOR,
                    "pct_chg": pct_chg if pct_chg is not None else 0.0,
                }
            )
            prev_close = close
        return pd.DataFrame(records, columns=DAILY_KLINE_COLUMNS)

    def _query_kline(self, bs: Any, bs_code: str, start_date: str, end_date: str) -> list[list[str]]:
        with _BS_LOCK:
            self._login(bs)
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,volume,amount,pctChg,tradestatus",
                    start_date=_to_dash_date(start_date),
                    end_date=_to_dash_date(end_date),
                    frequency="d",
                    adjustflag="2",
                )
                if rs.error_code != "0":
                    raise ProviderError(f"baostock K 线查询失败: {rs.error_msg}")
                rows: list[list[str]] = []
                while rs.next():
                    row = rs.get_row_data()
                    # row[8] 为 tradestatus，'1' 正常交易，过滤停牌
                    if len(row) >= 9 and row[8] == "0":
                        continue
                    rows.append(row[:8])
                return rows
            finally:
                self._logout(bs)

    # ==================== 基本信息 ====================

    def stock_basic(self) -> pd.DataFrame:
        """当前上市股票基本信息（best-effort，缺失字段填空）。"""
        bs = self._import_baostock()
        with _BS_LOCK:
            self._login(bs)
            try:
                rs = bs.query_stock_basic()
                if rs.error_code != "0":
                    raise ProviderError(f"baostock 基本信息查询失败: {rs.error_msg}")
                raw: list[list[str]] = []
                while rs.next():
                    raw.append(rs.get_row_data())
                fields = rs.fields
            finally:
                self._logout(bs)

        records: list[dict[str, Any]] = []
        for row in raw:
            item = dict(zip(fields, row, strict=False))
            bs_code = item.get("code", "")
            # 只保留股票（type=1），剔除指数 / 基金
            if item.get("type") not in ("1", "", None):
                continue
            if item.get("status") == "0":  # 已退市
                continue
            try:
                ts_code = baostock_code_to_ts_code(bs_code)
            except Exception:
                continue
            records.append(
                {
                    "ts_code": ts_code,
                    "name": item.get("code_name", ""),
                    "area": "",
                    "industry": "",
                    "market": infer_market_from_ts_code(ts_code),
                    "list_date": str(item.get("ipoDate", "")).replace("-", ""),
                    "is_hs": "",
                }
            )
        return pd.DataFrame(records, columns=STOCK_BASIC_COLUMNS)

    # ==================== 可选估值 ====================

    def daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """可选 PE/PB/PS（来自 K 线接口的 peTTM/pbMRQ/psTTM 字段）。"""
        bs = self._import_baostock()
        bs_code = ts_code_to_baostock(ts_code)
        with _BS_LOCK:
            self._login(bs)
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,peTTM,pbMRQ,psTTM",
                    start_date=_to_dash_date(start_date),
                    end_date=_to_dash_date(end_date),
                    frequency="d",
                    adjustflag="3",
                )
                if rs.error_code != "0":
                    raise ProviderError(f"baostock 估值查询失败: {rs.error_msg}")
                rows: list[list[str]] = []
                while rs.next():
                    rows.append(rs.get_row_data())
            finally:
                self._logout(bs)

        records: list[dict[str, Any]] = []
        for date_str, pe_ttm, pb, ps_ttm in rows:
            pe_ttm_v = safe_float(pe_ttm, default=None)
            ps_ttm_v = safe_float(ps_ttm, default=None)
            records.append(
                {
                    "ts_code": ts_code,
                    "trade_date": str(date_str).replace("-", ""),
                    "pe": pe_ttm_v,
                    "pe_ttm": pe_ttm_v,
                    "pb": safe_float(pb, default=None),
                    "ps": ps_ttm_v,
                    "ps_ttm": ps_ttm_v,
                    "total_mv": None,
                    "circ_mv": None,
                }
            )
        return pd.DataFrame(records, columns=DAILY_BASIC_COLUMNS)

    # ==================== 内部工具 ====================

    @staticmethod
    def _login(bs: Any) -> None:
        lg = bs.login()
        if lg.error_code != "0":
            raise ProviderError(f"baostock 登录失败: {lg.error_msg}")

    @staticmethod
    def _logout(bs: Any) -> None:
        try:
            bs.logout()
        except Exception:
            pass

    @staticmethod
    def _import_baostock() -> Any:
        try:
            import baostock as bs
        except ImportError as exc:
            raise ProviderError("缺少 baostock 依赖，请运行 uv sync --extra free-data") from exc
        return bs


def _to_dash_date(yyyymmdd: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD（baostock 入参格式）。"""
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd


def default_start_date(days: int = 730) -> str:
    """默认回溯起始日（YYYYMMDD）。"""
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
