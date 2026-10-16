# ADR-0004: 微信投递的 to_user_id 大小写与 agent-turn 投递

每日日报推送到微信，automation 采用 agent-turn（agent 会话执行），投递目标 `delivery.to` 必须使用**原始大小写**的接收者 id。

**Context**：T6 需要把日报推送到个人微信。实测（2026-10-12/13）发现微信投递的两个坑：

1. **command payload 的 `--announce` 投递失败**：报 `sendMessageWeixin: contextToken missing — refusing to send (upstream issue #247)`，或到达 iLink 后报 `ret=-3 invalid arguments`。微信 iLink 后端的主动外发要求每条消息携带"由该接收者入站消息签发的 account-scoped context token"；插件按 `(accountId, peer.toLowerCase())` 查 token。

2. **大小写敏感**（最终根因）：插件的 context token 存储 key 使用小写（`contextTokenKey` 内部 `toLowerCase()`），但**发给 iLink 的 `to_user_id` 是 `ctx.to` 原样**，iLink 端要求精确匹配接收者 id 的大小写。配置成小写 `to` 时 token 能查到但 iLink 报 `ret=-3`；配置成**大写原始形式**（bot 收到的 `from_user_id` 原样）后投递成功。

**Decision**：automation 使用 agent-turn（`--message`）payload，`delivery.to` 配置为接收者的原始大小写 id（形如 `<peer-id>@im.wechat`，即 account userId 形式），`delivery.accountId` 为 bot 账号 id。验证：run :4 `completion=succeeded, delivered=True`。

**Consequences**：
- 日报生成逻辑（抓取、汇总、排版）仍是脚本（ADR-0001），agent 负责"执行脚本 + 在会话中输出结果"，并对超长日报分块发送。
- 依赖 agent 正确执行多步（读 digest → 汇总 → 回复），通过 standing orders（已写入 OpenClaw workspace AGENTS.md）约束。
- **若更换微信账号/接收者，必须更新 `delivery.to` 为新接收者的原始大小写 id**——这是最容易踩的坑。

**Status**: accepted
