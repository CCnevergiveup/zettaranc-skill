# Skill 安装与改造状态

> 记录把 zettaranc-skill 从「仓库根的 SKILL.md 源文件」改造为「Claude Code 可加载的标准 skill」的进展。
> 最后更新：2026-06-26

## 背景与核心问题

本项目早期是 Python CLI 工程，后重构为「纯 Claude Code skill 分支」。但改造没做完最后一步：
`SKILL.md` 一直放在**仓库根目录**，而 Claude Code 只从 `.claude/skills/<name>/SKILL.md`、
`~/.claude/skills/<name>/SKILL.md`、插件目录三处发现 skill。

**结论**：放在根目录的 SKILL.md 不会被注册，用户说「切换到 Z 哥看 600519」无法触发——
能力层（Python 数据管线）是好的、方向也对，唯一断的是 skill 目录封装。

## 已完成 ✅

| 项 | 说明 | 验证 |
|----|------|------|
| **SKILL.md 安装到标准位置** | 新增 `.claude/skills/zettaranc-perspective/SKILL.md`（目录名 = frontmatter `name`） | Claude Code available skills 列表已出现 `zettaranc-perspective` |
| **SKILL.md 升级为 Schema-V2** | frontmatter 改为规范结构（Load when / Do NOT load when / Risk level / Data dependency / Output format）；补入四个 Surface 段：路由声明 / 契约 / 运行时资源索引 / 安全边界 | YAML 解析 OK，description 681 字符（< 1024 上限） |
| **数据源/命令保持免费源形态** | 全文无 Tushare/JNB/zt 残留，统一 `uv run scripts/*.py` + 免费数据源（baostock + AKShare） | grep Tushare/zt = 0 命中 |
| **cwd 鲁棒性说明** | 调用协议新增「工作目录基准」——脚本必须在仓库根执行，落在别处先 `cd` 回根 | 已写入 SKILL.md 调用协议段 |
| **.gitignore 放行 skill 入库** | 改为 `.claude/*` + `!.claude/skills/`，skill 目录入库、个人配置（settings.local.json）仍忽略 | `git check-ignore` 确认 skill 可追踪、settings 仍忽略 |
| **清理遗留 + 锁依赖** | 删除 `tushare.md`；纳入 `uv.lock` 锁定运行依赖 | 已提交 |
| **数据层未受影响** | 搬动 SKILL.md 后实测脚本仍正常 | `check_mode.py` → free/configured；`analyze.py 600519.SH` → 真实指标 JSON |
| **补入缺失的 heuristics.md** | 从 origin/main 取入 `knowledge/heuristics.md`（44 条决策启发式全量清单，SKILL.md 已引用、内容与免费源兼容） | 93 行，无 Tushare/zt 残留 |

**对应提交**：
- `3a37b66` feat(skill): 安装为标准 Claude Code skill 并升级 SKILL.md 为 Schema-V2
- `28e7b5c` feat(knowledge): 补入 heuristics.md(44条决策启发式全量清单)

## 未完成 / 刻意搁置 ⏸️

| 项 | 原因 | 后续建议 |
|----|------|---------|
| **推送 skill 分支到远端** | 推送时 github.com:443 连接被重置 / 超时（网络问题，非代码问题） | 用文末 push 命令手动推送 |
| **合并 origin/main 的 modules 重构** | main 对 `modules/` 是结构性重构（`price_patterns.py` 拆目录、删 `strategies/kirin.py`、重写 `screener.py`，+3905/-3718），不是孤立 bug fix。合进来会让 skill 分支的 `scripts/*.py` import 断裂，需逐个修脚本并重新验证，且与 skill 加载无关 | 如确需 main 的指标/策略改进，单独立项：先合 modules、再逐个修 scripts、重新跑通 analyze/screen/diagnose |
| **合并 origin/main 的工程目录** | `frontend/`、`api/`、`tests/`、`corpus/`、`docs/`、`.github/` 是 main 完整工程形态的产物；合进来等于推翻「精简成 skill 包」的设计 | 不建议合 —— 与 skill 分支定位冲突 |
| **合并 origin/main 的其余 knowledge/*.md** | 双向分叉：skill 分支 2026-05 改过、main 2026-06 也改过（+2613/-2410）。盲目用 main 版覆盖会丢失 skill 分支的编辑 | 如需，应逐文件人工比对，不可整目录覆盖 |
| **skill 完全自包含（可跨项目移植）** | 当前 skill 只装了 SKILL.md 单文件，scripts/modules/.env 仍在仓库根。隐式依赖「Claude Code 在仓库根启动」。已用 cwd 说明缓解，但拷到 `~/.claude/skills/` 跨项目用仍会断 | 如需移植性：把 scripts/modules 一并纳入 skill 目录，并改脚本路径锚定（改动大，与 data/ 在根目录等约定冲突，暂不做） |

## 分支关系备注

- **skill 分支**：纯 skill 包形态（免费数据源 + uv-run 脚本 + 包结构 modules）
- **origin/main**：完整工程形态（frontend + api + CLI + tests + CI + Tushare），领先 skill 40 个提交但与 skill 走的是两条路线
- 两者**不应直接 `git merge`** —— 会互相推翻对方的设计取舍。需要什么改进就挑选式合并（cherry-pick / 单文件取入）

## 如何验证 skill 已生效

1. 重启 Claude Code 会话（新建顶层 skills 目录需重启才被监听）
2. 在本仓库根目录启动 `claude`
3. 说「切换到 Z 哥，帮我看看 600519」→ 应触发 `zettaranc-perspective` skill 并自动调用 `uv run scripts/analyze.py 600519.SH`
