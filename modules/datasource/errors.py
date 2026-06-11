"""免费数据源异常体系。"""

from __future__ import annotations


class DataSourceError(Exception):
    """数据源通用错误基类。"""


class ProviderError(DataSourceError):
    """数据源 provider 运行错误（登录失败 / 查询失败 / 依赖缺失等）。"""


class ProviderImportError(ProviderError):
    """免费数据源依赖缺失（baostock / akshare 未安装）。"""


class CodeConvertError(DataSourceError):
    """股票代码 / 日期格式转换错误。"""
