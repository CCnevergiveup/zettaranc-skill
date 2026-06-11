"""免费数据源字段 / 代码转换（纯函数，便于单测）。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Final

import pandas as pd

from modules.datasource.errors import CodeConvertError
from modules.datasource.models import (
    MONEYFLOW_COLUMNS,
    MoneyflowRecord,
    Scalar,
)

# ==================== 股票代码转换 ====================


def ts_code_to_baostock(ts_code: str) -> str:
    """600487.SH -> sh.600487。"""
    code_num, market = _split_ts_code(ts_code)
    return f"{market.lower()}.{code_num}"


def baostock_code_to_ts_code(bs_code: str) -> str:
    """sh.600487 -> 600487.SH。"""
    parts = bs_code.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise CodeConvertError(f"无效 baostock 代码: {bs_code}")
    market, code_num = parts
    return f"{code_num}.{market.upper()}"


def ts_code_to_akshare_market(ts_code: str) -> tuple[str, str]:
    """600487.SH -> ('600487', 'sh')。"""
    code_num, market = _split_ts_code(ts_code)
    return code_num, market.lower()


def infer_market_from_ts_code(ts_code: str) -> str:
    """根据代码段推断板块名称。"""
    code_num, _ = _split_ts_code(ts_code)
    if code_num.startswith("688"):
        return "科创板"
    if code_num.startswith("300") or code_num.startswith("301"):
        return "创业板"
    if code_num.startswith(("830", "870", "871", "872", "873", "920")):
        return "北交所"
    if code_num.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "主板"
    return ""


def _split_ts_code(ts_code: str) -> tuple[str, str]:
    parts = ts_code.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise CodeConvertError(f"无效 ts_code: {ts_code}")
    return parts[0], parts[1]


# ==================== 日期 / 数值 ====================


def normalize_trade_date(value: object) -> str:
    """统一交易日期为 YYYYMMDD。"""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y%m%d")
    if isinstance(value, datetime | date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if not text:
        raise CodeConvertError("交易日期为空")
    if len(text) == 8 and text.isdigit():
        return text
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise CodeConvertError(f"无效交易日期: {text}") from exc


def safe_float(value: object, default: float | None = 0.0) -> float | None:
    """容错浮点转换：空值返回 default，百分号 / 千分位自动剥离。"""
    if value is None or (not isinstance(value, str | int | float) and value is not None):
        if value is None:
            return default
    try:
        if bool(pd.isna(value)):  # type: ignore[arg-type]
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if normalized.endswith("%"):
            normalized = normalized[:-1]
        if not normalized:
            return default
        try:
            return float(normalized)
        except ValueError:
            return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ==================== AKShare 资金流映射 ====================

_AK_ALIAS: Final[dict[str, tuple[str, ...]]] = {
    "date": ("日期", "trade_date"),
    "net_mf": ("主力净流入-净额", "主力净流入净额", "net_mf"),
    "pct_mf": ("主力净流入-净占比", "主力净流入净占比", "pct_mf"),
    "net_elg": ("超大单净流入-净额", "超大单净流入净额", "net_elg_amount"),
    "net_lg": ("大单净流入-净额", "大单净流入净额", "net_lg_amount"),
    "net_md": ("中单净流入-净额", "中单净流入净额", "net_md_amount"),
    "net_sm": ("小单净流入-净额", "小单净流入净额", "net_sm_amount"),
}

_AK_REQUIRED: Final[tuple[str, ...]] = (
    "date",
    "net_mf",
    "pct_mf",
    "net_elg",
    "net_lg",
    "net_md",
    "net_sm",
)


class AkshareMappingError(CodeConvertError):
    """AKShare 资金流字段映射错误。"""


def map_akshare_moneyflow_frame(
    df: pd.DataFrame,
    ts_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """将 stock_individual_fund_flow 历史资金流映射为 moneyflow 表兼容 DataFrame。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=MONEYFLOW_COLUMNS)

    aliases = _resolve_aliases(df, _AK_REQUIRED)
    rows: list[dict[str, Scalar]] = []
    for record in df.to_dict(orient="records"):
        trade_date = normalize_trade_date(record[aliases["date"]])
        if not _in_range(trade_date, start_date, end_date):
            continue
        rows.append(_map_full_row(record, ts_code, trade_date, aliases).as_dict())
    return pd.DataFrame(rows, columns=MONEYFLOW_COLUMNS)


def map_akshare_realtime_frame(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """fallback：stock_fund_flow_individual(即时) 粗字段，仅尽力填 net_mf。

    即时接口返回全市场快照（每行一只股票），必须按目标股票代码过滤出对应行；
    该接口不提供大单 / 超大单分层，buy_*/sell_* 全部保留 None；净额映射到 net_mf，
    净额缺失时 net_mf 亦为 None，调用方可识别为降级数据。
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=MONEYFLOW_COLUMNS)

    code_num, _ = ts_code_to_akshare_market(ts_code)
    code_col = _find_realtime_code_column(df)
    if code_col is None:
        return pd.DataFrame(columns=MONEYFLOW_COLUMNS)

    matched = df[df[code_col].astype(str).str.zfill(6) == code_num]
    if matched.empty:
        return pd.DataFrame(columns=MONEYFLOW_COLUMNS)

    rows = [_map_realtime_row(record, ts_code).as_dict() for record in matched.to_dict(orient="records")]
    return pd.DataFrame(rows, columns=MONEYFLOW_COLUMNS)


def _find_realtime_code_column(df: pd.DataFrame) -> str | None:
    """即时接口的股票代码列（不同版本可能为 股票代码/代码）。"""
    columns = {str(column) for column in df.columns}
    for candidate in ("股票代码", "代码", "code"):
        if candidate in columns:
            return candidate
    return None


def _map_full_row(
    record: Mapping[str, object],
    ts_code: str,
    trade_date: str,
    aliases: Mapping[str, str],
) -> MoneyflowRecord:
    elg = safe_float(record[aliases["net_elg"]], default=None)
    lg = safe_float(record[aliases["net_lg"]], default=None)
    md = safe_float(record[aliases["net_md"]], default=None)
    sm = safe_float(record[aliases["net_sm"]], default=None)
    return MoneyflowRecord(
        ts_code=ts_code,
        trade_date=trade_date,
        buy_sm_amount=_pos(sm),
        buy_md_amount=_pos(md),
        buy_lg_amount=_pos(lg),
        buy_elg_amount=_pos(elg),
        sell_sm_amount=_neg(sm),
        sell_md_amount=_neg(md),
        sell_lg_amount=_neg(lg),
        sell_elg_amount=_neg(elg),
        net_mf=safe_float(record[aliases["net_mf"]], default=None),
        pct_mf=safe_float(record[aliases["pct_mf"]], default=None),
    )


def _map_realtime_row(record: Mapping[str, object], ts_code: str) -> MoneyflowRecord:
    trade_date = _realtime_trade_date(record)
    return MoneyflowRecord(
        ts_code=ts_code,
        trade_date=trade_date,
        buy_sm_amount=None,
        buy_md_amount=None,
        buy_lg_amount=None,
        buy_elg_amount=None,
        sell_sm_amount=None,
        sell_md_amount=None,
        sell_lg_amount=None,
        sell_elg_amount=None,
        # 即时接口仅提供"净额"粗字段（且常带 万/亿 单位字符串，safe_float 解析失败时为 None），无净占比
        net_mf=_optional(record, ("净额", *_AK_ALIAS["net_mf"])),
        pct_mf=None,
    )


def _realtime_trade_date(record: Mapping[str, object]) -> str:
    for alias in _AK_ALIAS["date"]:
        if alias in record and not _is_missing(record[alias]):
            return normalize_trade_date(record[alias])
    return date.today().strftime("%Y%m%d")


def _optional(record: Mapping[str, object], aliases: tuple[str, ...]) -> float | None:
    for alias in aliases:
        if alias in record:
            return safe_float(record[alias], default=None)
    return None


def _resolve_aliases(df: pd.DataFrame, logical_fields: tuple[str, ...]) -> dict[str, str]:
    columns = {str(column) for column in df.columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for field in logical_fields:
        alias = next((a for a in _AK_ALIAS[field] if a in columns), None)
        if alias is None:
            missing.append(f"{field}({'/'.join(_AK_ALIAS[field])})")
        else:
            resolved[field] = alias
    if missing:
        raise AkshareMappingError(f"AKShare 资金流字段缺失: {', '.join(missing)}")
    return resolved


def _in_range(trade_date: str, start_date: str | None, end_date: str | None) -> bool:
    if start_date is not None and trade_date < start_date:
        return False
    if end_date is not None and trade_date > end_date:
        return False
    return True


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _pos(value: float | None) -> float:
    if value is None or value <= 0:
        return 0.0
    return value


def _neg(value: float | None) -> float:
    if value is None or value >= 0:
        return 0.0
    return abs(value)
