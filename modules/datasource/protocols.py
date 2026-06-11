"""数据源协议定义。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from modules.datasource.models import (
    DailyBasicRecord,
    DailyKlineRecord,
    MoneyflowRecord,
    StockBasicRecord,
)


@runtime_checkable
class MarketDataProvider(Protocol):
    """统一行情数据源协议。

    所有 provider 只负责"拉取 + 规范化到标准 record"，
    不写库、不做业务派生（如涨跌停标记），由 DataSyncer 统一编排。
    """

    name: str
    max_workers: int

    def stock_basic(self) -> list[StockBasicRecord]:
        """返回当前上市股票基本信息。"""
        ...

    def daily_kline(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[DailyKlineRecord]:
        """返回前复权日线（YYYYMMDD 区间，闭区间）。"""
        ...

    def daily_basic(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[DailyBasicRecord]:
        """返回估值指标（可选；不支持时返回空列表）。"""
        ...

    def moneyflow(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MoneyflowRecord]:
        """返回个股资金流（可选；不支持时返回空列表）。"""
        ...
