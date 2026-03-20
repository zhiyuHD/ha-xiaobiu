# Design: HA IAR Regression Rollback

## Context

用户反馈最近几轮 HA IAR 修复把行为越修越差。

最新 HA 后端日志已经把失败点收敛到：

- `custom_components.suning_biu.config_flow.async_step_captcha_done()`
- 恢复 `_async_send_sms(captcha)` 时进入 `client.send_sms_code()`
- 最终抛出 `SuningError: 验证码发送失败，请稍后重试(00201)`

用户明确选择的方案是：回滚 `1b72b07` 的功能性改动，只保留日志增强，优先恢复到“HA 里 IAR 通过后，至少能成功请求短信验证码”的状态。

## Discovery Results

- `dbd5806` 是用户明确反馈“至少还能请求验证码”的基线版本。
- `dbd5806..1b72b07` 在 HA IAR 主链路上的唯一核心功能变化，是把 `iarVerifyCodeTicket` 的申请时机从 eager 改成 deferred。
- 旧链路：
  - [`config_flow.py`](/root/workspace/suning/custom_components/suning_biu/config_flow.py) 在捕获 `CaptchaRequiredError(isIarVerifyCode)` 后立即申请 ticket
  - [`iar_external_view.py`](/root/workspace/suning/custom_components/suning_biu/iar_external_view.py) 只负责渲染已持有 ticket 的页面，并接收单次成功回调
- 新链路：
  - `iar_external_view` 新增 `prepare` 阶段
  - 浏览器先上报 `detect/dfpToken`
  - HA 再申请 ticket
  - 页面再初始化 `SnCaptcha`
- 现有新证据只能证明 `sendCode.do` 在恢复阶段返回了业务错误 `00201`，不足以证明 deferred-ticket 是正确修复，反而与用户反馈共同指向它是回归源。

## Requirements

- 回滚 `1b72b07` 引入的 deferred-ticket / `prepare` 协议改动。
- 保留 `config_flow.async_step_captcha_done()` 中新增的异常日志，继续暴露底层错误。
- 保留 unsupported captcha `risk_type` 的错误日志。
- 不改变已验证过的 HA external-step 能力 URL 模式。
- 不破坏已经存在的浏览器风控上下文采集、成功回调幂等保护、session 生命周期保护。
- 测试层面要同步回退只服务于 deferred-ticket 模型的断言。

## Rationale

推荐这个设计的原因只有一个：它是当前证据下风险最低、验证边界最清晰的方案。

- 用户目标不是继续探索新协议，而是先恢复“至少能发短信”。
- 当前真实后端错误已经暴露，继续保留 `1b72b07` 再叠加补丁，只会扩大不确定性。
- 回滚范围集中在 `1b72b07` 对 HA IAR 时序的改动，变更面最小。
- 保留日志增强后，即使回滚后仍失败，也可以继续基于真实异常定位，而不是再次根据前端 HAR 现象猜根因。

## Detailed Design

### 1. 回滚 `config_flow` 的 deferred-ticket 行为

在 [`config_flow.py`](/root/workspace/suning/custom_components/suning_biu/config_flow.py) 的 `_async_send_sms()` 中恢复旧行为：

- 捕获 `CaptchaRequiredError(isIarVerifyCode)` 后立即调用 `self._client.request_iar_verify_code_ticket(self._phone_number)`
- 使用返回的 `ticket` 创建 IAR session
- 不再把 `client` / `phone_number` 注入 session

保留：

- `async_step_captcha_done()` 中对恢复失败的 `_LOGGER.exception(...)`
- unsupported `risk_type` 的 `_LOGGER.error(...)`

### 2. 回滚 `iar_external_view` 的双阶段协议

在 [`iar_external_view.py`](/root/workspace/suning/custom_components/suning_biu/iar_external_view.py) 恢复单阶段模型：

- `IARCaptchaSession.ticket` 恢复为必填字符串
- 删除 `client`
- 删除 `phone_number`
- 删除 `prepared_detect`
- 删除 `prepared_dfp_token`
- 删除 `_async_prepare_ticket()`
- 删除 `action=prepare` / `action=complete` 分支
- 恢复为浏览器只提交一次 `token + detect + dfpToken`

保留：

- `flow_id + nonce` capability URL 模式
- `resume_requested` 幂等保护
- 缺少 `detect/dfpToken` 时拒绝回调

### 3. 回滚验证码页 JS 的 `prepare` 阶段

在 [`custom_components/suning_biu/suning_biu_ha/captcha_bridge.py`](/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/captcha_bridge.py) 和 [`src/suning_biu_ha/captcha_bridge.py`](/root/workspace/suning/src/suning_biu_ha/captcha_bridge.py) 中：

- 删除 `window.__CAPTCHA_PREPARE_URL__`
- 删除 `window.__CAPTCHA_INITIAL_TICKET__`
- 删除 `prepareCaptchaTicket()`
- 删除 `bootstrapCaptcha()` 两阶段初始化
- 恢复为页面加载后直接 `SnCaptcha.init(ticket=<已提供 ticket>)`

保留：

- 风控脚本加载
- `detect/dfpToken` 轮询采集
- success callback 的单次提交开关 `captchaSubmitStarted`

### 4. 测试调整

测试以回到 eager-ticket 模型为目标：

- 恢复或重写 `test_iar_captcha_step_updates_risk_context_before_retry`
  - 断言 session 创建时已有 `ticket`
- 重写 `test_iar_captcha_view_serves_page_and_triggers_flow_resume`
  - 页面 GET 直接包含 ticket
  - 不再要求 `prepare` 请求
- 删除 `test_iar_captcha_view_rejects_complete_before_prepare`
- 新增 `caplog` 断言
  - 恢复失败时日志包含 `Failed to resume Suning SMS flow after IAR verification`

## Design Documents

- [BDD Specifications](./bdd-specs.md) - Behavior scenarios and testing strategy
- [Architecture](./architecture.md) - System architecture and component details
- [Best Practices](./best-practices.md) - Security, performance, and code quality guidelines
