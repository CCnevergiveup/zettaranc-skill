"""
启动向导模块
用户首次使用时引导配置数据源：free 模式（免费数据源 baostock + AKShare）或 websearch（纯角色对话）
"""

import os
from pathlib import Path

# dotenv 加载已移至 modules/__init__.py（包级别一次性加载）

# 数据模式别名
MODE_FREE = "free"  # 免费数据源模式：baostock + AKShare
MODE_NORMAL = "websearch"  # 普通小万模式：纯角色对话
MODE_NAMES = {
    MODE_FREE: "免费数据源",
    MODE_NORMAL: "普通小万",
}


def check_env_exists() -> bool:
    """检查 .env 文件是否存在且配置了有效数据模式"""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return False

    data_mode = os.environ.get("DATA_MODE", "")
    return data_mode in (MODE_FREE, MODE_NORMAL)


def check_data_mode() -> str | None:
    """返回当前数据模式：free / websearch / None（未配置）"""
    return os.environ.get("DATA_MODE", None)


def get_mode_display_name(mode: str) -> str:
    """获取模式显示名称"""
    return MODE_NAMES.get(mode, mode)


def write_env_file(mode: str = MODE_FREE) -> str:
    """
    写入 .env 文件

    Args:
        mode: 数据模式，"free" 或 "websearch"

    Returns:
        .env 文件的绝对路径
    """
    env_path = Path(__file__).parent.parent / ".env"
    lines = [
        "# 数据模式: free(免费数据源 baostock+AKShare) 或 websearch(普通小万/纯角色对话)",
        f"DATA_MODE={mode}",
        "",
        "# 免费源组合: composite(默认, baostock+AKShare) / baostock / akshare",
        "FREE_DATA_PROVIDER=composite",
        "",
        "# 数据库路径（相对于项目根目录）",
        "DATA_DIR=data",
        "DB_PATH=data/stock_data.db",
        "",
    ]

    env_path.write_text("\n".join(lines), encoding="utf-8")

    # 同时设置环境变量，使当前会话立即生效
    os.environ["DATA_MODE"] = mode

    return str(env_path)


def run_wizard():
    """
    运行启动向导（命令行模式，agent 对话中不直接使用）

    流程：
    1. 检查是否已配置
    2. 询问用户选择数据模式
    3. 写入 .env 并确认
    """
    print("=" * 50)
    print("  Zettaranc 启动向导")
    print("=" * 50)
    print()

    # 检查是否已配置
    if check_env_exists():
        mode = check_data_mode()
        display = get_mode_display_name(mode)
        print(f"[已配置] 当前模式: {display}")
        print()
        print("如需重新配置，请删除 .env 文件后重新运行")
        return mode

    print("欢迎使用 Zettaranc！请选择模式：")
    print()
    print("  [1] 免费数据源 — baostock + AKShare（开箱即用，无需 Token）")
    print("  [2] 普通小万 — 纯角色对话（不走行情接口）")
    print()

    while True:
        choice = input("请选择 [1/2]: ").strip()
        if choice in ("1", "2"):
            break
        print("  请输入 1 或 2")

    mode = MODE_FREE if choice == "1" else MODE_NORMAL
    env_path = write_env_file(mode=mode)
    print(f"配置已写入: {env_path}")
    print(f"{get_mode_display_name(mode)}模式已启用")
    return mode


if __name__ == "__main__":
    mode = run_wizard()
    print(f"\n最终模式: {get_mode_display_name(mode)}")
