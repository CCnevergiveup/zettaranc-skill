"""免费数据源 PoC 验证脚本

目标：验证 baostock(K线) + akshare(资金流) 能否替代 Tushare 中转，
并能否直接喂给本项目现有的砖形图算法。

运行：uv run --with baostock --with akshare --with pandas python scripts/poc_free_datasource.py
"""

import sys
from pathlib import Path

# 让 PoC 能 import 本项目的砖形图算法
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.indicators.core import DailyData  # noqa: E402
from modules.indicators.price_patterns import (  # noqa: E402
    calculate_brick_value,
    calculate_brick_history,
    detect_four_brick_system,
)

TS_CODE = "600487.SH"  # 测试标的：亨通光电


# ============ 1. baostock 拉前复权日线 ============
def fetch_kline_baostock(ts_code: str, days: int = 120) -> list[DailyData]:
    import baostock as bs

    # 本项目代码用 600487.SH，baostock 用 sh.600487 格式，做一次转换
    code_num, market = ts_code.split(".")
    bs_code = f"{market.lower()}.{code_num}"

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")

    try:
        # adjustflag=2 前复权（与本项目 pro_bar(adj='qfq') 对齐）
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount,pctChg",
            start_date="2026-01-01",
            frequency="d",
            adjustflag="2",
        )
        if rs.error_code != "0":
            raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
    finally:
        bs.logout()

    rows = rows[-days:]
    klines: list[DailyData] = []
    prev_close = 0.0
    for r in rows:
        date, o, h, low, c, vol, amt, pct = r
        # baostock 空字段返回 ""，做容错
        klines.append(
            DailyData(
                ts_code=ts_code,
                trade_date=date.replace("-", ""),
                open=float(o or 0),
                high=float(h or 0),
                low=float(low or 0),
                close=float(c or 0),
                vol=float(vol or 0),
                amount=float(amt or 0),
                pct_chg=float(pct or 0),
                prev_close=prev_close,
            )
        )
        prev_close = float(c or 0)
    return klines


# ============ 2. akshare 拉个股资金流 ============
def fetch_moneyflow_akshare(ts_code: str) -> dict:
    import akshare as ak

    code_num, market = ts_code.split(".")
    df = ak.stock_individual_fund_flow(stock=code_num, market=market.lower())
    if df is None or df.empty:
        return {}

    latest = df.iloc[-1]  # 最新一日
    # 映射到本项目 moneyflow 表语义（净流入额，单位元）
    return {
        "trade_date": str(latest["日期"]),
        "net_mf_main": float(latest["主力净流入-净额"]),       # 主力 = 大单+超大单
        "net_elg": float(latest["超大单净流入-净额"]),          # 特大单
        "net_lg": float(latest["大单净流入-净额"]),             # 大单
        "net_md": float(latest["中单净流入-净额"]),
        "net_sm": float(latest["小单净流入-净额"]),
        "pct_mf_main": float(latest["主力净流入-净占比"]),
        "close": float(latest["收盘价"]),
        "pct_chg": float(latest["涨跌幅"]),
    }


def main() -> None:
    print("=" * 60)
    print(f"免费数据源 PoC 验证 — {TS_CODE}")
    print("=" * 60)

    # ---- baostock K线 + 砖形图 ----
    print("\n[1] baostock 前复权日线 → 本项目砖形图算法")
    try:
        klines = fetch_kline_baostock(TS_CODE, days=120)
        print(f"    ✓ 拉取 {len(klines)} 根 K 线")
        if klines:
            last = klines[-1]
            print(f"    最新: {last.trade_date} 收盘={last.close} 涨跌={last.pct_chg}%")

            brick_val = calculate_brick_value(klines)
            trend, count = calculate_brick_history(klines)
            four_brick = detect_four_brick_system(klines)
            print(f"    ✓ 砖值 brick_value = {brick_val}")
            print(f"    ✓ 砖型趋势 = {trend}, 连续 {count} 块")
            print(f"    ✓ 四块砖操作建议 = {four_brick['brick_action']} — {four_brick['brick_action_desc']}")
    except Exception as e:
        print(f"    ✗ baostock 失败: {e!r}")

    # ---- akshare 资金流 ----
    print("\n[2] akshare 个股资金流 → 本项目 moneyflow 字段映射")
    try:
        mf = fetch_moneyflow_akshare(TS_CODE)
        if mf:
            print(f"    ✓ 最新资金流日期 = {mf['trade_date']}")
            print(f"    ✓ 主力净流入(净额) = {mf['net_mf_main']:,.0f} 元 ({mf['pct_mf_main']}%)")
            print(f"    ✓ 特大单净流入     = {mf['net_elg']:,.0f} 元")
            print(f"    ✓ 大单净流入       = {mf['net_lg']:,.0f} 元")
            print("    → 战法层 large_inflow = 大单+特大单聚合，net_mf = 主力净流入，字段可映射")
        else:
            print("    ✗ akshare 返回空")
    except Exception as e:
        print(f"    ✗ akshare 失败: {e!r}")

    print("\n" + "=" * 60)
    print("结论：两个免费源能否替代 Tushare 中转，看上面 ✓/✗")
    print("=" * 60)


if __name__ == "__main__":
    main()
