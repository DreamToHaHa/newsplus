# OpenClaw 运行环境（WSL）

本项目的编排层运行于 WSL2 中的 OpenClaw。本文档记录环境事实与关键踩坑点，供实现 T6/T7/T8 及后续维护参考。

## 运行状态（2026-10-12 验证）

- **版本**：`OpenClaw 2026.9.4 (3a9d69d)` — 注意：**非最新版**，为微信插件兼容而降级
- **位置**：WSL2 Ubuntu，用户 `<user>`，npm 全局安装于 `~/.nvm/versions/node/v24.18.0/bin/openclaw`
- **Gateway**：systemd 用户服务 `openclaw-gateway` running，端口 18789
- **微信渠道**：`openclaw-weixin`（社区版 3.2.3）enabled/running，账号 `<bot-account-id>`
- **默认模型**：`volcengine-agent-plan/deepseek-v4.1-flash`
- **兜底模型**：`volcengine-agent-plan/ark-code-latest`
- **Provider**：`volcengine-agent-plan`，baseUrl `https://ark.cn-beijing.volces.com/api/plan/v3`，协议 `api: openai-responses`
- **Dashboard**：http://127.0.0.1:18789

从 Windows 侧访问：`wsl -e bash -lc 'export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH"; openclaw ...'`

## 关键技术坑

### 坑 1：微信插件与 openclaw 2026.10.2 不兼容 → 必须降级到 2026.9.4
- openclaw 2026.10.2 移除了 3 个旧插件 SDK 导出（`plugin-sdk/infra-runtime`、`plugin-sdk/channel-message`、`plugin-sdk/command-auth`）
- 微信插件（腾讯官方 2.4.x、社区版 3.2.3）都依赖这些导出 → 在 2026.10.2 上无法加载
- 社区版 `openclaw-weixin` 3.2.3 基于 **2026.9.4** 构建，降级后可用
- **结论**：微信可用性与核心版本强绑定。未来升级核心前，先确认微信插件已适配新 SDK。

### 坑 2：降级触发 openclaw 防降级保护
- gateway 拒绝启动：`binary older than config last written by 2026.10.2`
- `OPENCLAW_ALLOW_OLDER_BINARY_DESTRUCTIVE_ACTIONS=1` 在 systemd 服务模式下被过滤，drop-in 无效
- 正确解法：编辑 `~/.openclaw/openclaw.json` 的 `meta.lastTouchedVersion` 从 `"2026.10.2"` 改为 `"2026.9.4"`

### 坑 3：数据库 schema 版本不向后兼容
- 2026.10.2 把 state 库升到 schema v20、agent 库升到 v24；2026.9.4 只支持 v17
- 解法：删除 `~/.openclaw/state/openclaw.sqlite` 和 `~/.openclaw/agents/main/agent/openclaw-agent.sqlite` 让 2026.9.4 重建
- API key 不在这两个库里（明文在 openclaw.json），删库不影响认证

### 坑 4：配置兼容（降级后）
- 2026.9.4 不识别 `meta.migrations.utilityModelSeparation` → 用 jq 删除
- 兜底模型字段 `agents.defaults.model.fallbacks` 在 2026.9.4 同样支持（已验证）

### 坑 5：火山 agent plan 的协议
- 实际接入协议是 **`api: openai-responses`**（不是 anthropic-messages，也不是用户文档里的 `/api/plan` 路径）
- baseUrl 用 `/api/plan/v3` 实测连通

## 备份文件（保留，勿删）

位于 WSL `~` 下（确认长期稳定后可删）：
- `~/openclaw-backup-20261012-170239.tar.gz`（重装前旧配置）
- `~/openclaw-state-backup-20261012-222940.tar.gz`（降级前 state 库）
- `~/openclaw-agentdb-backup-20261012-223455.tar.gz`（降级前 agent 库）

## 安全注意

- 火山引擎 API key 明文存于 `~/.openclaw/openclaw.json`，勿提交到 git，勿写入本仓库任何文件
- 微信登录凭证设备绑定，勿泄露
- 本仓库 `data/` 目录已在 .gitignore，抓取数据与去重状态不入库

## 更新决策（ADR）

- ADR-0001 记录"用 OpenClaw 作编排层"，并已注明"OpenClaw 重装与全部配置均由实现时执行"
- 本文档补充了该 ADR 未涵盖的运行环境细节与降级约束，未来升级核心前请重读本文档坑 1
