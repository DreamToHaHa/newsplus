# ADR-0002: 推送目标为个人微信

汇总结果推送到**个人微信账号**（QR 扫码登录），而非企业微信 WeCom。

**Context**：用户的使用场景是"每天把汇总推到我自己的微信"，个人微信体验最符合直觉。但存在两条路：个人微信（扫码接入，Tencent 官方插件 `@tencent-weixin/openclaw-weixin`）和企业微信 WeCom（`@wecom/wecom-openclaw-plugin`，零封号风险但需额外装企业微信 App）。

**Decision**：选择个人微信。用户明确拍板接受个人号自动化的账号风控/封号风险，换取最直接的"推到我微信"体验。

**Consequences**：登录方式为手机扫码确认；个人号自动化存在账号风险，属已知且接受的权衡。若日后风控出现问题，切换到 WeCom 是低成本回退（OpenClaw 频道层抽象一致）。

**Status**: accepted
