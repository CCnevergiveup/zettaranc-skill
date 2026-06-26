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
"""个股分析脚本：指标 + 主力阶段 + 战法信号 + 持仓诊断 + 综合评分。

由模型在用户问「帮我看看 XX」「XX 能不能买」时调用，输出 JSON 供模型用
Z 哥口吻包装回复。Python 只做数据准备，不生成话术。

用法：
    uv run scripts/analyze.py 600519.SH
    uv run scripts/analyze.py 600519.SH --days 120

依赖说明：
    PEP723 声明含 baostock/akshare（免费数据源模式所需）。本 skill 单机单工程
    使用，uv 仅首次解析安装一次，无需顾虑体积。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 注入项目根目录，使脚本能 import modules 包（modules/__init__.py 会自动加载 .env）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def analyze(ts_code: str, days: int) -> dict:
    """复用各能力模块完成完整分析，返回结构化字典。"""
    from modules.indicators import analyze_stock, detect_three_waves, detect_kirin_stage
    from modules.indicators.data_layer import get_kline_data, DailyData
    from modules.strategies import detect_all_strategies
    from modules.portfolio_diagnosis import diagnose_stock
    from modules.screener import analyze_stock as screener_analyze

    # 1. 技术指标
    result = analyze_stock(ts_code, days=days)

    # 2. 主力阶段（三波理论 + 麒麟会），数据不足时静默跳过
    wave_data = None
    kirin_data = None
    klines = get_kline_data(ts_code, days=days)
    if klines:
        daily_klines = []
        for i, k in enumerate(klines):
            prev_close = klines[i - 1].close if i > 0 else k.close
            daily_klines.append(
                DailyData(
                    ts_code=k.ts_code,
                    trade_date=k.trade_date,
                    open=k.open,
                    high=k.high,
                    low=k.low,
                    close=k.close,
                    vol=k.vol,
                    amount=k.amount,
                    pct_chg=k.pct_chg,
                    prev_close=prev_close,
                )
            )
        wave_data = detect_three_waves(daily_klines)
        kirin_data = detect_kirin_stage(daily_klines)

    # 3. 战法信号
    signals = detect_all_strategies(ts_code, days=days)

    # 4. 持仓诊断
    diagnosis = diagnose_stock(ts_code, days=days)

    # 5. 综合评分
    score = screener_analyze(ts_code)

    return {
        "ts_code": ts_code,
        "name": getattr(diagnosis, "name", ts_code),
        "price": getattr(diagnosis, "price", 0),
        "indicators": {
            "kdj": {"k": result.k, "d": result.d, "j": result.j},
            "macd": {
                "dif": result.dif,
                "dea": result.dea,
                "hist": result.macd_hist,
                "veto": getattr(diagnosis, "macd_veto", False),
            },
            "bbi": result.bbi,
            "ma": {"ma5": result.ma5, "ma10": result.ma10, "ma20": result.ma20},
            "rsi": {"rsi6": result.rsi6, "rsi12": result.rsi12, "rsi24": result.rsi24},
            "brick": {"trend": result.brick_trend, "count": result.brick_count, "value": result.brick_value},
        },
        "waves": {
            "type": wave_data["wave"] if wave_data else "未知",
            "confidence": wave_data["confidence"] if wave_data else 0,
            "suggestion": wave_data.get("b1_suggestion") if wave_data else None,
        },
        "kirin": {
            "stage": kirin_data["stage"] if kirin_data else "未知",
            "confidence": kirin_data["confidence"] if kirin_data else 0,
            "operation": kirin_data.get("operation") if kirin_data else None,
        },
        "strategies": [
            {
                "strategy": s.strategy.value,
                "date": s.trade_date,
                "confidence": s.confidence,
                "action": s.action,
                "priority": s.priority.value,
                "description": s.description,
            }
            for s in signals[:10]
        ],
        "diagnosis": {
            "price_position": getattr(diagnosis, "price_position", ""),
            "trend_status": getattr(diagnosis, "trend_status", ""),
            "sell_score": getattr(diagnosis, "sell_score", 0),
            "sell_score_desc": getattr(diagnosis, "sell_score_desc", ""),
            "kirin_phase": getattr(diagnosis, "kirin_phase", ""),
            "risk_level": getattr(diagnosis, "risk_level", ""),
            "recommendation": getattr(diagnosis, "recommendation", ""),
        },
        "score": {
            "total": score.score,
            "b1_score": score.b1_score,
            "trend_score": score.trend_score,
            "volume_score": score.volume_score,
            "risk_score": score.risk_score,
            "rating": score.rating,
            "reasons": score.reasons,
            "warnings": score.warnings,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="个股分析（指标+主力+战法+诊断+评分）")
    parser.add_argument("ts_code", help="股票代码，如 600519.SH")
    parser.add_argument("--days", type=int, default=120, help="分析天数（默认 120）")
    args = parser.parse_args()

    try:
        data = analyze(args.ts_code, args.days)
    except Exception as exc:  # 失败时输出结构化错误，供模型用 Z 哥口吻转述
        print(json.dumps({"error": str(exc), "ts_code": args.ts_code}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
