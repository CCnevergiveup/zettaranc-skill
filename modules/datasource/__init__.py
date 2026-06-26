"""免费数据源接入层。

提供 baostock / AKShare 免费数据源（baostock 负责 K 线/基本信息/估值，AKShare 负责资金流）。
上层 indicators/strategies 仍只读 SQLite，本包只负责"拉取 + 规范化"。
"""

from modules.datasource.factory import create_free_provider

__all__ = ["create_free_provider"]
