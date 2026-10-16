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

- **工作目录**：OpenClaw 运行于本机 WSL 中（2026.9.4，微信插件兼容而降级）；抓取脚本挂在其 automations 调度器下。运行环境细节与踩坑见 `docs/openclaw-environment.md`。
- **架构**：抓取（Python，全量入库）→ 模型链汇总（OpenClaw provider：primary + fallbacks）→ **邮件推送**。见 `docs/adr/0001-openclaw-as-orchestrator.md`。
- **推送通道**：邮件（HTML 日报，收件人由 `mailpush` 管理）；模型链顺序从 `openclaw.json` 读，密钥存 `data/providers.json`（不入 git）。
- **用户决策**：抓取全量，用户决策只影响推送（权威规则存 `data/preferences.json`，agent 通过 `src/daily/preferences_cli.py` 写入）。见 `docs/adr/0003-user-preference-filter.md`。
- **提交前**：跑 `bash scripts/scan-secrets.sh` 扫敏感信息（真实 key / 邮箱 / 个人标识），勿把真实标识写进提交。
- **GitHub CLI**：`gh` 不在系统 PATH，用完整路径 `/c/Program Files/GitHub CLI/gh.exe`（或先 `export PATH="$PATH:/c/Program Files/GitHub CLI"`）。

For Claude Code specifics, see `CLAUDE.md`.
