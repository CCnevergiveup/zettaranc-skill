# zettaranc（万千）· Claude Code Skill

> 「股票最难的地方不是选股和买入，而是卖出。利润是市场给的，都是概率的事儿，谁也别吹牛逼。」

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)

这是一个给 **Claude Code** 使用的 AI Skill：把 zettaranc（万千）的投资、职业、人生决策框架封装在 `SKILL.md`，并保留真实行情数据脚本作为确定性数据准备层。

核心原则只有一句：

> **用户用自然语言沟通；Claude Code 判断意图后自己调用 `uv run scripts/*.py`；Python 只做数据准备，分析话术由模型用 Z 哥角色生成。**

本分支不是传统 Python CLI 工程，也不再提供 `zt` 命令、测试工程、CI、语料采集流水线。它是一个可直接放进 Claude Code 使用的 skill 包。

---

## 目录结构

```text
.
├── SKILL.md                 # Skill 入口：角色协议、调用规则、问诊流程、自我改进协议
├── scripts/                 # Claude Code 通过 Bash 调用的 uv-run 脚本
│   ├── check_mode.py         # 检查 .env / DATA_MODE
│   ├── setup_mode.py         # 配置 free / websearch 模式
│   ├── sync.py               # 初始化数据库、同步行情和指标
│   ├── analyze.py            # 个股分析：指标 + 战法 + 诊断 + 评分
│   ├── screen.py             # 选股扫描
│   ├── diagnose.py           # 持仓诊断
│   ├── backtest.py           # 回测：少妇 / 多策略 / 组合
│   ├── trade.py              # 交易记录与复盘数据包
│   ├── track.py              # 自我改进：跟踪池 + 跟踪数据同步
│   └── review.py             # 自我改进：月度复盘 + Guardrails 建议
├── modules/                 # 数据准备能力层：指标、战法、数据源、回测、复盘、tracking
├── knowledge/               # Z 哥框架参考资料，按需被模型读取
├── references/              # 调研来源与溯源资料
├── assets/                  # 静态资源
├── pyproject.toml           # 项目元数据与本地开发依赖
└── requirements.txt         # 非 uv 场景的依赖参考
```

---

## 快速开始

### 1. 准备环境

需要本机已安装：

- Claude Code
- `uv`

克隆并进入仓库：

```bash
git clone <repo-url>
cd zettaranc-skill
git checkout skill
```

> 日常使用不需要 `pip install -e .`，也不需要手动运行 `zt`。脚本顶部带 PEP723 依赖声明，Claude Code 调用 `uv run scripts/*.py` 时会自动准备依赖。

### 2. 配置数据模式

推荐直接让 Claude Code 处理：

```text
切换到 Z 哥，用这个 skill。帮我检查数据模式。
```

Claude 会按 `SKILL.md` 自动调用：

```bash
uv run scripts/check_mode.py
```

如果需要手动调试，也可以运行：

```bash
# 免费数据源：baostock + AKShare，开箱即用（默认推荐）
uv run scripts/setup_mode.py --mode free

# 纯角色对话，不走行情接口
uv run scripts/setup_mode.py --mode websearch
```

`.env.example` 已给出完整配置模板。

### 3. 开始自然语言使用

你不需要记命令。直接和 Claude Code 说：

```text
用 Z 哥视角帮我看看 600519.SH，现在能不能买？
```

Claude Code 会：

1. 读取 `SKILL.md` 判断这是股票问题；
2. 自己调用 `uv run scripts/analyze.py 600519.SH`；
3. 读取 JSON 数据；
4. 用 Z 哥口吻输出判断。

---

## 脚本能力清单

这些脚本主要给 Claude Code 调用。手动运行仅用于调试。

| 用户自然语言意图 | Claude Code 调用 | 作用 |
|---|---|---|
| 「帮我看看 XX」 | `uv run scripts/analyze.py <code>` | 指标 + 战法 + 主力阶段 + 诊断 + 评分 |
| 「现在能买什么」 | `uv run scripts/screen.py --strategy B1 --limit 10` | 选股扫描 |
| 「帮我诊断一下 XX」 | `uv run scripts/diagnose.py <code>` | 持仓诊断 |
| 「回测一下 XX」 | `uv run scripts/backtest.py shaofu <code>` | 少妇战法回测 |
| 「多策略回测 XX」 | `uv run scripts/backtest.py multi <code>` | 多策略融合回测 |
| 「组合回测」 | `uv run scripts/backtest.py portfolio <codes>` | 多股票组合回测 |
| 「我今天买了 XX」 | `uv run scripts/trade.py add "<描述>"` | 解析并保存交易 |
| 「复盘这笔交易」 | `uv run scripts/trade.py review` | 生成交易复盘数据包 |
| 「同步一下数据」 | `uv run scripts/sync.py sync <code>` | 同步 K 线 + 指标 |
| 「把这几只票加入跟踪」 | `uv run scripts/track.py add <code>` | 加入自我改进跟踪池 |
| 「复盘这个月」 | `uv run scripts/review.py monthly YYYY-MM` | 月度复盘 |
| 「该优化哪些策略」 | `uv run scripts/review.py strategy YYYY-MM` | 策略表现 + Guardrails 建议 |

---

## 自我改进闭环

本 skill 保留 tracking / review / harness 逻辑，但改变交互方式：不再让用户手动跑 CLI，而是 Claude Code 在对话中驱动。

流程：

```text
自然语言添加跟踪股票
  ↓
Claude 调用 track.py 写入 tracking_pool_self
  ↓
定期同步跟踪数据，记录 K 线 / 指标 / 信号
  ↓
Claude 调用 review.py 生成月度复盘和策略表现
  ↓
Claude 读取建议，向用户提议是否修改 SKILL.md / knowledge
  ↓
用户确认后，Claude 才用 Edit 落地修改
```

重要约束：

- `review.py` 和 `harness_updater.py` **只生成建议，不自动改文件**。
- 修改 `SKILL.md` / `knowledge/` 必须有真实跟踪数据或语料支撑。
- Claude 必须先说明准备改什么、为什么改、依据是什么；用户确认后再改。

这让本项目可以在 Claude Code 中形成「越用越准」的个人化闭环。

---

## 数据模式

| 模式 | 说明 | 适合场景 |
|---|---|---|
| `free` | 免费数据源（baostock + AKShare），无需 Token | 推荐默认模式 |
| `websearch` | 不走行情接口，只使用角色框架与外部搜索 | 只聊思维框架、职业/人生/商业判断 |

---

## 手动调试示例

通常不用手敲这些命令，但调试时可以直接运行：

```bash
# 检查模式
uv run scripts/check_mode.py

# 初始化数据库（含 tracking 的 _self 表）
uv run scripts/sync.py init

# 同步并分析个股
uv run scripts/sync.py sync 600519.SH --days 365
uv run scripts/analyze.py 600519.SH

# 选股
uv run scripts/screen.py --strategy B1 --limit 10

# 回测
uv run scripts/backtest.py shaofu 600519.SH --days 250

# 跟踪池与复盘
uv run scripts/track.py add 600519.SH --reason "B1买点" --strategy B1
uv run scripts/track.py sync 600519.SH --days 365
uv run scripts/review.py monthly 2026-05
uv run scripts/review.py strategy 2026-05
```

---

## 设计边界

本分支刻意移除了旧工程形态中的内容：

- 不提供 `zt` CLI 入口；
- 不保留测试工程、CI、语料采集工具、开发文档；
- 不内置 LLM / RAG / 聊天服务；
- 不让用户手动执行业务流程脚本。

保留的是 skill 真正需要的部分：

- `SKILL.md` 角色协议；
- `knowledge/` 和 `references/` 渐进式披露资料；
- `modules/` 确定性数据准备能力；
- `scripts/` 模型可触发的 uv-run 接口；
- SQLite / JSONL 持久化的自我改进闭环。

---

## 免责声明

本项目用于学习、研究和个人决策辅助，不构成投资建议。市场有风险，交易需自负盈亏。Z 哥风格回答由 AI 基于公开语料与本项目规则生成，不代表本人观点。
