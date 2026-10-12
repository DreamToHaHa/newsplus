# CLAUDE.md

Claude Code 专用约定文件。项目的主约定见 [AGENTS.md](AGENTS.md)（通用 agent 约定），本文件补充 Claude Code 专属要点。

## 指向主约定

完整约定、Agent skills、领域文档与约束见 [AGENTS.md](AGENTS.md)。请先阅读它。

## Claude Code 补充要点

- **语言**：与用户交流使用中文。
- **git**：提交信息用中文或英文均可，保持简洁。
- **gh 调用**：`gh` 不在系统 PATH，用完整路径 `/c/Program Files/GitHub CLI/gh.exe`，或先 `export PATH="$PATH:/c/Program Files/GitHub CLI"`。
