"""免费数据源统一模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

Scalar = str | float | int | None


@dataclass(frozen=True)
class StockBasicRecord:
    """stock_basic 表兼容行。"""

    ts_code: str
    name: str
    area: str
    industry: str
    market: str
    list_date: str
    is_hs: str

    def as_dict(self) -> dict[str, Scalar]:
        """转换为可写入 DataFrame 的字典。"""
        return asdict(self)


@dataclass(frozen=True)
class DailyKlineRecord:
    """daily_kline 表兼容行。"""

    ts_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    vol: float
    amount: float
    pct_chg: float

    def as_dict(self) -> dict[str, Scalar]:
        """转换为可写入 DataFrame 的字典。"""
        return asdict(self)


@dataclass(frozen=True)
class DailyBasicRecord:
    """daily_kline 估值扩展列兼容行。"""

    ts_code: str
    trade_date: str
    pe: float | None
    pe_ttm: float | None
    pb: float | None
    ps: float | None
    ps_ttm: float | None
    total_mv: float | None
    circ_mv: float | None

    def as_dict(self) -> dict[str, Scalar]:
        """转换为可写入 DataFrame 的字典。"""
        return asdict(self)


@dataclass(frozen=True)
class MoneyflowRecord:
    """moneyflow 表兼容行。"""

    ts_code: str
    trade_date: str
    buy_sm_amount: float | None
    buy_md_amount: float | None
    buy_lg_amount: float | None
    buy_elg_amount: float | None
    sell_sm_amount: float | None
    sell_md_amount: float | None
    sell_lg_amount: float | None
    sell_elg_amount: float | None
    net_mf: float | None
    pct_mf: float | None

    def as_dict(self) -> dict[str, Scalar]:
        """转换为可写入 DataFrame 的字典。"""
        return asdict(self)


STOCK_BASIC_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "name",
    "area",
    "industry",
    "market",
    "list_date",
    "is_hs",
)

DAILY_KLINE_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "vol",
    "amount",
    "pct_chg",
)

DAILY_BASIC_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "total_mv",
    "circ_mv",
)

MONEYFLOW_COLUMNS: tuple[str, ...] = (
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
)
