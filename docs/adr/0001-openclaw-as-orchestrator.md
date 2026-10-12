# ADR-0001: 用 OpenClaw 作为抓取之外的编排与推送底座

方案的第一版用 OpenClaw 承担"调度、汇总、推送微信"整个编排层：代码只负责抓取原始条目，OpenClaw 的 automations（cron）调度器定时唤醒 agent，用 command/script payload 直接运行抓取脚本，agent 汇总后通过微信通道投递。

**Context**：需要一个每天自动运行的"抓取 → 汇总 → 推微信"流水线。备选方案是自建调度器（Windows 任务计划 + 自写推送代码 + 第三方微信通道如 Server酱）。

**Decision**：选择 OpenClaw 作为编排层。依据（2026-10-12 查证 openclaw.ai 与 docs.openclaw.ai）：
- OpenClaw 是开源个人 AI 助手（GitHub 34.6 万星），原生支持部署到本机（Windows x64/ARM64、npm/一键安装），无订阅、无托管层。
- 原生微信通道：外部插件 `@tencent-weixin/openclaw-weixin`（腾讯微信官方团队维护），个人微信 QR 扫码登录即可收发；另支持企业微信 WeCom（`@wecom/wecom-openclaw-plugin`，腾讯 WeCom 团队维护）。
- 内置调度器 automations/cron：支持一次性与循环任务、4 种 payload（系统事件/agent 消息/command/shell 脚本/script 代码脚本）、投递到聊天频道或 webhook、运行历史、失败通知。command payload 可 `--announce --channel <channel> --to <target>` 直接投递。

**Consequences**：抓取代码与 OpenClaw 之间的边界必须清晰——抓取只产数据，OpenClaw 只消费。抓取代码需以 OpenClaw 可调用的形态存在（command 或 script payload 指向的脚本）。个人微信自动化存在账号风险，需在访谈中决定是否用企业微信 WeCom 替代。

**Status**: accepted
**Accepted 2026-10-12**: 调度宿主确定为 OpenClaw automations（Q1-a）；抓取语言 Python（Q7，效果不佳时切换 Node/TS）；推送时间为北京时间每天 20:00（Q5）；LLM provider 为火山引擎方舟 agent plan（Q6）；接收对象为专用小号（Q4）；推送内容超长时分多条发完整（Q6）。模型配置：默认 `deepseek-v4.1-flash`，兜底 `ark-code-latest`。OpenClaw 重装与全部配置均由实现时执行。
