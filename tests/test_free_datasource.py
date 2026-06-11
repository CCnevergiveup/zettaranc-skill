"""免费数据源映射单测（纯函数，不联网）。"""

from __future__ import annotations

import pandas as pd
import pytest

from modules.datasource.codecs import (
    AkshareMappingError,
    baostock_code_to_ts_code,
    infer_market_from_ts_code,
    map_akshare_moneyflow_frame,
    map_akshare_realtime_frame,
    normalize_trade_date,
    safe_float,
    ts_code_to_akshare_market,
    ts_code_to_baostock,
)
from modules.datasource.errors import CodeConvertError


# ==================== 代码转换 ====================


class TestCodeConvert:
    def test_ts_code_to_baostock(self):
        assert ts_code_to_baostock("600487.SH") == "sh.600487"
        assert ts_code_to_baostock("000001.SZ") == "sz.000001"

    def test_baostock_code_to_ts_code(self):
        assert baostock_code_to_ts_code("sh.600487") == "600487.SH"
        assert baostock_code_to_ts_code("sz.000001") == "000001.SZ"

    def test_ts_code_to_akshare_market(self):
        assert ts_code_to_akshare_market("600487.SH") == ("600487", "sh")
        assert ts_code_to_akshare_market("300750.SZ") == ("300750", "sz")

    def test_invalid_ts_code(self):
        with pytest.raises(CodeConvertError):
            ts_code_to_baostock("600487")

    def test_invalid_baostock_code(self):
        with pytest.raises(CodeConvertError):
            baostock_code_to_ts_code("600487")

    def test_infer_market(self):
        assert infer_market_from_ts_code("688981.SH") == "科创板"
        assert infer_market_from_ts_code("300750.SZ") == "创业板"
        assert infer_market_from_ts_code("600487.SH") == "主板"
        assert infer_market_from_ts_code("000001.SZ") == "主板"


# ==================== 日期 / 数值 ====================


class TestNormalize:
    def test_normalize_trade_date(self):
        assert normalize_trade_date("2026-06-10") == "20260610"
        assert normalize_trade_date("20260610") == "20260610"
        assert normalize_trade_date(pd.Timestamp("2026-06-10")) == "20260610"

    def test_normalize_trade_date_invalid(self):
        with pytest.raises(CodeConvertError):
            normalize_trade_date("")

    def test_safe_float(self):
        assert safe_float("1.5") == 1.5
        assert safe_float("1,234.5") == 1234.5
        assert safe_float("12%") == 12.0
        assert safe_float(None) == 0.0
        assert safe_float(None, default=None) is None
        assert safe_float("", default=None) is None
        assert safe_float("abc", default=None) is None


# ==================== AKShare 资金流映射 ====================


def _make_eastmoney_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "日期": "2026-06-09",
                "收盘价": 105.02,
                "涨跌幅": 10.0,
                "主力净流入-净额": 1.6e9,
                "主力净流入-净占比": 9.57,
                "超大单净流入-净额": 1.7e9,
                "超大单净流入-净占比": 10.02,
                "大单净流入-净额": -7.8e7,
                "大单净流入-净占比": -0.45,
                "中单净流入-净额": -8.8e8,
                "中单净流入-净占比": -5.04,
                "小单净流入-净额": -7.9e8,
                "小单净流入-净占比": -4.53,
            },
            {
                "日期": "2026-06-10",
                "收盘价": 106.88,
                "涨跌幅": 1.77,
                "主力净流入-净额": -3.07e8,
                "主力净流入-净占比": -1.36,
                "超大单净流入-净额": -1.2e8,
                "超大单净流入-净占比": -0.53,
                "大单净流入-净额": -1.87e8,
                "大单净流入-净占比": -0.83,
                "中单净流入-净额": -9.9e7,
                "中单净流入-净占比": -0.44,
                "小单净流入-净额": 4.06e8,
                "小单净流入-净占比": 1.79,
            },
        ]
    )


class TestAkshareMoneyflowMapping:
    def test_map_full_frame(self):
        df = map_akshare_moneyflow_frame(_make_eastmoney_frame(), "600487.SH")
        assert len(df) == 2
        # 第二行：主力净流出，大单/超大单为负 → sell_*，净额拆分正确
        row = df[df["trade_date"] == "20260610"].iloc[0]
        assert row["ts_code"] == "600487.SH"
        assert row["net_mf"] == pytest.approx(-3.07e8)
        assert row["pct_mf"] == pytest.approx(-1.36)
        assert row["sell_elg_amount"] == pytest.approx(1.2e8)
        assert row["sell_lg_amount"] == pytest.approx(1.87e8)
        assert row["buy_elg_amount"] == 0.0
        # 小单为正 → buy_sm_amount
        assert row["buy_sm_amount"] == pytest.approx(4.06e8)
        assert row["sell_sm_amount"] == 0.0

    def test_map_positive_inflow_row(self):
        df = map_akshare_moneyflow_frame(_make_eastmoney_frame(), "600487.SH")
        row = df[df["trade_date"] == "20260609"].iloc[0]
        # 超大单为正 → buy_elg
        assert row["buy_elg_amount"] == pytest.approx(1.7e9)
        assert row["sell_elg_amount"] == 0.0

    def test_date_range_filter(self):
        df = map_akshare_moneyflow_frame(
            _make_eastmoney_frame(), "600487.SH", start_date="20260610", end_date="20260610"
        )
        assert len(df) == 1
        assert df.iloc[0]["trade_date"] == "20260610"

    def test_empty_frame(self):
        df = map_akshare_moneyflow_frame(pd.DataFrame(), "600487.SH")
        assert df.empty
        assert list(df.columns) == [
            "ts_code",
            "trade_date",
            "buy_sm_amount",
            "buy_md_amount",
            "buy_lg_amount",
            "buy_elg_amount",
            "sell_sm_amount",
            "sell_md_amount",
            "sell_lg_amount",
            "sell_elg_amount",
            "net_mf",
            "pct_mf",
        ]

    def test_missing_columns_raises(self):
        bad = pd.DataFrame([{"日期": "2026-06-10", "收盘价": 1.0}])
        with pytest.raises(AkshareMappingError):
            map_akshare_moneyflow_frame(bad, "600487.SH")


def _make_realtime_frame() -> pd.DataFrame:
    """模拟同花顺即时接口（stock_fund_flow_individual(symbol="即时")）的全市场快照。"""
    return pd.DataFrame(
        [
            {"序号": 1, "股票代码": "300894", "股票简称": "火星人", "最新价": 11.38, "净额": 4.06e8},
            {"序号": 2, "股票代码": "600487", "股票简称": "亨通光电", "最新价": 106.88, "净额": -3.07e8},
        ]
    )


class TestAkshareRealtimeFallback:
    def test_realtime_filters_target_code(self):
        # 即时接口返回全市场快照，必须只映射出目标股票那一行
        out = map_akshare_realtime_frame(_make_realtime_frame(), "600487.SH")
        assert len(out) == 1
        row = out.iloc[0]
        assert row["ts_code"] == "600487.SH"
        assert row["net_mf"] == pytest.approx(-3.07e8)
        # 即时接口无净占比，且不伪造盘口分层
        assert row["pct_mf"] is None
        assert row["buy_lg_amount"] is None
        assert row["sell_elg_amount"] is None

    def test_realtime_unmatched_code_empty(self):
        out = map_akshare_realtime_frame(_make_realtime_frame(), "000001.SZ")
        assert out.empty
