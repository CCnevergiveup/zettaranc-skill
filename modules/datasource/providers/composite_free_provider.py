"""免费组合数据源：baostock 提供 K 线/基本信息/估值，AKShare 提供资金流。"""

from __future__ import annotations

import logging

import pandas as pd

from modules.datasource.models import MONEYFLOW_COLUMNS
from modules.datasource.providers.akshare_provider import AkshareProvider
from modules.datasource.providers.baostock_provider import BaostockProvider

logger = logging.getLogger(__name__)


class CompositeFreeProvider:
    """组合免费数据源（baostock + AKShare）。"""

    name = "free-composite"

    def __init__(self, max_workers: int = 1) -> None:
        # baostock 登录态与 AKShare 免费接口都不宜高并发，默认串行
        self.max_workers = max_workers
        self._baostock = BaostockProvider(max_workers=max_workers)
        self._akshare = AkshareProvider(max_workers=max_workers)

    # ==================== baostock ====================

    def stock_basic(self) -> pd.DataFrame:
        """股票基本信息（baostock）。"""
        return self._baostock.stock_basic()

    def daily_kline(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """前复权日线（baostock）。"""
        return self._baostock.daily_kline(ts_code, start_date, end_date)

    def daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """可选估值 PE/PB/PS（baostock）。"""
        return self._baostock.daily_basic(ts_code, start_date, end_date)

    # ==================== AKShare ====================

    def moneyflow(self, ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        """个股资金流（AKShare），失败不抛出，返回空表，避免阻断 K 线同步。"""
        try:
            return self._akshare.moneyflow(ts_code, start_date, end_date)
        except Exception as exc:
            logger.warning("AKShare 资金流获取失败 %s: %s", ts_code, exc)
            return pd.DataFrame(columns=MONEYFLOW_COLUMNS)
