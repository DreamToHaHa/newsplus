# newsplus — Agent conventions

AI 源头信息每日推送项目：每日抓取 5 个 AI 信息源，汇总后推送到个人微信。

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues on `DreamToHaHa/newsplus`, managed via `gh` CLI (installed at `C:\Program Files\GitHub CLI\gh.exe`). See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage labels are `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Key constraints

- **工作目录**：OpenClaw 运行于本机 WSL 中；抓取脚本挂在其 automations 调度器下。
- **架构**：抓取（Python，全量入库）→ OpenClaw 汇总（火山引擎模型）→ 个人微信推送。见 `docs/adr/0001-openclaw-as-orchestrator.md`。
- **微信**：推送目标为个人微信，扫码登录。见 `docs/adr/0002-personal-wechat-channel.md`。
- **用户决策**：抓取全量，用户决策只影响推送（对话式表达，记入 USER.md）。见 `docs/adr/0003-user-preference-filter.md`。
- **GitHub CLI**：`gh` 不在系统 PATH，用完整路径 `/c/Program Files/GitHub CLI/gh.exe`（或先 `export PATH="$PATH:/c/Program Files/GitHub CLI"`）。

For Claude Code specifics, see `CLAUDE.md`.
