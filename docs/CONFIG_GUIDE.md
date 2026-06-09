# 配置指南

> 所有配置项均通过 `.env` 文件管理，复制 `.env.example` 后按需修改。
>
> 本项目面向 Claude Code（及 Cursor 等支持文件读取与命令调用的宿主）使用：
> **角色与知识由宿主直接读取 `SKILL.md` / `knowledge/` / `rules/`，数据由 `zt` CLI 提供。**
> 因此无需配置任何 LLM / 向量知识库服务。

---

## 核心配置

### 数据模式

```ini
DATA_MODE=jnb
```

| 值 | 说明 | 依赖 |
|---|------|------|
| `jnb` | 接入 Tushare 真实行情数据，开启指标计算、选股、回测、诊断 | 必须配置 `TUSHARE_TOKEN` + `TUSHARE_API_URL` |
| `websearch` | 不连接行情接口，仅做角色对话（由宿主读取 `SKILL.md` / `knowledge/` 回答） | 无需 Tushare 配置 |

---

## 数据层配置（仅 jnb 模式）

### Tushare API

```ini
TUSHARE_TOKEN=你的56位token
TUSHARE_API_URL=https://你的中转地址
TUSHARE_VERIFY_TOKEN_URL=
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `TUSHARE_TOKEN` | 是（jnb） | Tushare Pro 的 56 位 Token，在 https://tushare.pro/user/token 获取 |
| `TUSHARE_API_URL` | 是（jnb） | 中转 API 地址，从 Tushare 中转服务商获取 |
| `TUSHARE_VERIFY_TOKEN_URL` | 否 | 实时行情验证地址，一般不需要 |

**注意**：如果 `DATA_MODE` 不是 `jnb`，这些配置可以为空，程序不会报错。

---

## 数据库配置

```ini
DATA_DIR=data
DB_PATH=data/stock_data.db
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATA_DIR` | `data` | 数据目录 |
| `DB_PATH` | `data/stock_data.db` | SQLite 数据库路径，支持绝对/相对路径 |

---

## 配置示例

### 纯对话模式（无需任何外部服务）

```ini
DATA_MODE=websearch
```

宿主（Claude Code）直接读取 `SKILL.md`、`knowledge/`、`rules/` 提供 Z 哥风格回答，不调用任何行情接口。

### 股票全功能模式（需 Tushare）

```ini
DATA_MODE=jnb
TUSHARE_TOKEN=你的56位token
TUSHARE_API_URL=https://你的中转地址
DATA_DIR=data
DB_PATH=data/stock_data.db
```

配置完成后即可使用 `zt analyze` / `zt screen` / `zt diagnose` / `zt backtest` 等全部量化命令。
