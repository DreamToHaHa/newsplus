# ADR-0004: 微信投递走 agent 会话而非 command announce

每日日报推送到微信，采用 **agent-turn（agent 会话执行）** 方式，而不是 command payload 的 `--announce` 投递。

**Context**：T6 需要把日报推送到个人微信。初始设计用 command payload 的 `--announce --channel openclaw-weixin --to <peer>` 投递 stdout。实测（2026-10-12）失败：微信插件（NewFuture/openclaw-weixin 3.2.3）报 `sendMessageWeixin: contextToken missing — refusing to send (upstream issue #247)`，且 `--target` 的小写/大写 id 变体均不通。

**根因**：微信 iLink 后端的**主动外发**要求每条消息携带"由该接收者入站消息签发的 account-scoped context token"。插件 README 明确承认此限制（token 缺失或过期则拒发）。而 **agent 在微信会话中回复**是插件的设计主路径——agent 携带会话上下文，天然有该接收者的 token。

**Decision**：automation 使用 agent-turn（`--message` payload），让 agent 在微信会话上下文中执行"读取日报 → 生成汇总 → 回复到当前会话"。已验证：用户给 bot 发消息，bot 能正常回复，证明 agent 会话路径可用。

**Consequences**：
- 日报生成逻辑（抓取、汇总、排版）仍是脚本（ADR-0001 的脚本主链路不变），agent 负责"执行脚本 + 在会话中输出结果"。
- 依赖 agent 正确执行多步（读 digest.json → 汇总 → 回复），可靠性与 agent 指令清晰度相关——通过 standing orders（已写入 OpenClaw workspace AGENTS.md）约束。
- command announce 的 contextToken 问题绕开，但未来若插件修复该限制，可切回更确定的 announce 路径。

**Status**: accepted
