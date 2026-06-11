"""免费数据源接入层。

提供 baostock / AKShare 免费数据源，与现有 Tushare 中转可切换。
上层 indicators/strategies 仍只读 SQLite，本包只负责"拉取 + 规范化"。
"""

from modules.datasource.factory import create_free_provider

__all__ = ["create_free_provider"]
