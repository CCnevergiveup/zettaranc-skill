"""AKShare 免费数据源 provider（个股资金流）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from modules.datasource.codecs import (
    map_akshare_moneyflow_frame,
    map_akshare_realtime_frame,
    ts_code_to_akshare_market,
)
from modules.datasource.errors import ProviderError


class AkshareProvider:
    """AKShare 数据源 provider。"""

    name = "akshare"

    def __init__(self, max_workers: int = 1) -> None:
        self.max_workers = max_workers

    def moneyflow(self, ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        """个股资金流，映射为 moneyflow 表兼容字段；主源失败回退即时接口。"""
        ak = self._import_akshare()
        stock, market = ts_code_to_akshare_market(ts_code)
        try:
            df = ak.stock_individual_fund_flow(stock=stock, market=market)
        except Exception:
            return self._realtime_fallback(ak, ts_code)
        return map_akshare_moneyflow_frame(df, ts_code, start_date, end_date)

    def _realtime_fallback(self, ak: Any, ts_code: str) -> pd.DataFrame:
        """fallback：stock_fund_flow_individual(即时) 粗字段降级。"""
        try:
            df = ak.stock_fund_flow_individual(symbol="即时")
        except Exception:
            return pd.DataFrame()
        if df is None:
            return pd.DataFrame()
        return map_akshare_realtime_frame(df, ts_code)

    @staticmethod
    def _import_akshare() -> Any:
        try:
            import akshare as ak
        except ImportError as exc:
            raise ProviderError("缺少 AKShare 依赖，请运行 uv sync --extra free-data（akshare>=1.18.64）") from exc
        return ak
