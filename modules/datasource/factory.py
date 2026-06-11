"""数据源工厂：按 DATA_MODE / FREE_DATA_PROVIDER 选择 provider。"""

from __future__ import annotations

import os
from typing import Any

from modules.datasource.errors import ProviderError


def get_free_max_workers(default: int = 1) -> int:
    """免费源并发线程数（FREE_DATA_MAX_WORKERS，默认保守串行）。"""
    raw = os.environ.get("FREE_DATA_MAX_WORKERS", "")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 1 else default


def create_free_provider() -> Any:
    """根据 FREE_DATA_PROVIDER 创建免费数据源 provider。"""
    provider_name = os.environ.get("FREE_DATA_PROVIDER", "composite").lower()
    max_workers = get_free_max_workers()

    if provider_name in ("composite", "free", "free-composite"):
        from modules.datasource.providers.composite_free_provider import CompositeFreeProvider

        return CompositeFreeProvider(max_workers=max_workers)
    if provider_name == "baostock":
        from modules.datasource.providers.baostock_provider import BaostockProvider

        return BaostockProvider(max_workers=max_workers)
    if provider_name == "akshare":
        from modules.datasource.providers.akshare_provider import AkshareProvider

        return AkshareProvider(max_workers=max_workers)

    raise ProviderError(f"未知 FREE_DATA_PROVIDER: {provider_name}，可选 composite/baostock/akshare")
