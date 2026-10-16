# newsplus

AI 源头信息每日推送：每天定时抓取 5 个 AI 信息源，用大模型汇总成中文日报，以 HTML 邮件推送到指定邮箱。

灵感来自一条 X 推文——"跳过中间商，直接盯源头"。本项目把 arXiv、Hugging Face Papers、The Batch 等一手信息源聚合起来，每天一封邮件，不用逐个网站翻。

## 它做什么

```
每天 20:00（可配）
  → 抓取 5 个信息源的新增条目（全量入库）
  → 按用户偏好过滤（关键词黑名单 / 关闭某些源）
  → 调用大模型生成：今日要点概述 + 每条一句中文点评
  → 渲染成 HTML 日报，邮件推送到所有收件人
  → 失败源跳过 + 本地日志，日报后附失败告警
```

## 信息源

| 源 | 抓取方式 | 内容 |
|---|---|---|
| [news.smol.ai](https://news.smol.ai) | RSS | AINews 每日周报（标题 + 完整 markdown 正文） |
| [arXiv cs.AI](https://arxiv.org/list/cs.AI/recent) | HTML 列表页 | 标题 + 作者 + 主题（列表页无摘要） |
| [Hugging Face Papers](https://huggingface.co/papers) | HTML 卡片 | 论文标题 + 链接 |
| [The Batch](https://www.deeplearning.ai/the-batch/) | HTML | 吴恩达团队周报（每周一期，4 篇文章） |
| [alphaXiv](https://alphaxiv.org) | JSON-LD | 热门论文（标题 + 描述） |

**5 个源均无需登录**，匿名抓取公开页面。这也是刻意的设计：匿名抓取拿到的"公开视图"每天口径一致，不会因人而异。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│  OpenClaw（编排层，WSL 本机运行）                              │
│                                                              │
│  cron automation（每天 20:00）                                │
│     → 运行 daily pipeline（Python 脚本）                       │
│     → 结果邮件推送到收件人列表                                  │
│                                                              │
│  模型链：primary + fallbacks（额度用尽自动切换）                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  Python 脚本（src/）
   fetchers/  抓取 5 源 → 结构化条目 → 去重入库
   daily/     过滤 → 模型汇总 → 渲染 HTML → 邮件发送
```

- **抓取层**（`src/fetchers/`）：每个源一个模块，注入式 fetcher/parser，统一条目模型 + JSON 去重存储
- **流水线层**（`src/daily/`）：偏好过滤、模型汇总、HTML 渲染、邮件发送
- **编排层**：OpenClaw 负责定时触发（cron），模型和收件人配置复用 OpenClaw 生态

## 快速开始

### 前置

- Python 3.12+
- （推荐）WSL2 + OpenClaw（用于定时调度）；也可手动运行

### 安装

```bash
pip install -e ".[dev]"    # 或 pip install feedparser requests pytest
```

### 配置

**1. 模型 provider**：`data/providers.json`（不入 git）

```json
{
  "providers": {
    "opencode-go": {
      "api_key": "<你的 key>",
      "headers": { "x-opencode-session": "$SESSION" },
      "session_id": "newsplus-daily"
    }
  }
}
```

模型链顺序（用哪个 provider、额度用尽后落到哪个）从 OpenClaw 的 `~/.openclaw/openclaw.json` 读取：
`agents.defaults.model.primary` + `agents.defaults.model.fallbacks`。**在 OpenClaw 里换模型，newsplus 自动跟随。**

**2. 邮件收件人**：由 `mailpush` 工具管理（`~/.openclaw-mailpush/config.json`）

```bash
python3 ~/.openclaw-mailpush/mailpush.py add you@example.com 你的名字
python3 ~/.openclaw-mailpush/mailpush.py list
```

**3. 用户偏好（可选）**：`data/preferences.json`

```bash
# 不推送含"强化学习"的条目
python3 -m src.daily.preferences_cli --action add-keyword --value "强化学习"
# 关闭某个源
python3 -m src.daily.preferences_cli --action disable-source --value thebatch
# 查看当前规则
python3 -m src.daily.preferences_cli --action list
```

### 运行

```bash
# 完整流程：抓取 → 汇总 → 发邮件
python3 -m src.daily.run --mode email

# 或仅预览（stdout，不发送）
python3 -m src.daily.run --mode stdout
```

## ⚠️ 数据准确性提醒（重要）

**抓取的数据由脚本自动获取，未经人工核验。** 使用前请抽查核对：

- **arXiv**：列表页只含标题/作者/主题，**无摘要**；日报中的"点评"是模型基于标题生成的概括，可能不准确
- **Hugging Face Papers**：卡片页只含标题和链接，**无摘要**
- **模型生成内容**：今日要点概述、逐条点评均为大模型生成，**可能存在事实偏差或幻觉**，仅供参考；关键信息请以原文链接为准
- **数据时效**：默认覆盖最近 36 小时的新增条目；周报类源（The Batch）无更新时自然缺席
- 所有原始抓取数据保留在 `data/items.json`，可随时核对

## 配置项（模型链与环境）

| 项 | 位置 | 说明 |
|---|---|---|
| 模型 provider 顺序 | `~/.openclaw/openclaw.json` | `agents.defaults.model.primary` / `.fallbacks` |
| provider 密钥 | `data/providers.json` | 不入 git（`data/` 已忽略） |
| 邮件收件人/SMTP | `~/.openclaw-mailpush/config.json` | 由 mailpush 工具管理 |
| 用户偏好 | `data/preferences.json` | 关键词黑名单 + 源开关 |
| 抓取数据 | `data/items.json` | 全量条目 + 去重状态 |
| 失败日志 | `data/daily-errors.log` | 源、错误、时间 |

## 项目文档

- [GLOSSARY.md](GLOSSARY.md) — 领域术语
- [AGENTS.md](AGENTS.md) — Agent 约定
- [docs/adr/](docs/adr/) — 架构决策记录（ADR）
  - `0001` OpenClaw 作编排层
  - `0002` 个人微信推送（历史，已被邮件替代）
  - `0003` 用户决策过滤
  - `0004` 微信投递机制
- [docs/openclaw-environment.md](docs/openclaw-environment.md) — OpenClaw 运行环境与踩坑记录

## 开发

```bash
python -m pytest tests/ -q     # 跑测试（108 个）
```

测试采用固定夹具（各源真实 HTML/RSS 样本），不依赖网络。

## 已知限制

- 抓取仅覆盖各源**公开视图**，不含登录后的个性化内容
- 模型汇总质量依赖所配模型；额度用尽会自动落到 fallback
- alphaXiv 用首页 JSON-LD（Trending Papers），非全文

## 许可

私有项目。
