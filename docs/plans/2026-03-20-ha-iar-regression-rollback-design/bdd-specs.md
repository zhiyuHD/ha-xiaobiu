# BDD Specifications for HA IAR Regression Rollback

## Feature: Restore eager-ticket HA IAR flow

### Scenario: 进入 IAR 步骤时立即拿到 ticket

Given HA config flow 在首次 `send_sms_code(..., captcha=None)` 时收到 `CaptchaRequiredError(isIarVerifyCode)`
When flow 创建 IAR external step
Then IAR session 应立即保存已申请好的 `ticket`
And 浏览器首次打开 external-step 页面时不需要额外 `prepare` 请求

### Scenario: IAR 成功后恢复短信发送

Given flow 已进入 IAR external step
And 当前 IAR session 已包含 `ticket`
And 浏览器回传 `token + detect + dfpToken`
When `async_step_captcha_done()` 恢复执行
Then client 应先更新风险上下文
And 再使用 `CaptchaSolution(kind="iar")` 重试 `send_sms_code`
And 成功时 flow 应进入 `sms_code`

### Scenario: IAR 成功后短信恢复失败

Given flow 已进入 IAR external step
And 浏览器已成功回传 `token + detect + dfpToken`
When 恢复阶段的 `send_sms_code` 抛出 `SuningError`
Then flow 应回到带 `cannot_connect` 的 `user` 表单
And 当前 IAR session 不应被提前丢弃
And HA 日志应记录恢复失败异常

### Scenario: IAR 页面重复 success callback

Given 同一个 IAR session 已收到一次成功回调
When 浏览器或前端重复再次提交相同成功 payload
Then HA 只应恢复 flow 一次
And 重复请求应返回幂等成功结果

### Scenario: 风险上下文缺失时拒绝恢复

Given IAR 页面没有拿到完整 `detect/dfpToken`
When 浏览器提交回调
Then HA 应拒绝该回调
And flow 不应继续重试发短信

## Testing Strategy

### Unit tests

- 覆盖 `_async_send_sms()` 在 IAR 分支创建 session 时已经持有 `ticket`
- 覆盖 `async_step_captcha_done()` 的风险上下文更新与恢复发送
- 覆盖恢复失败时回到 `user` 表单并记录日志

### Integration-style component tests

- 覆盖 `iar_external_view` 的 GET/POST 单阶段协议
- 覆盖缺少风险上下文时拒绝回调
- 覆盖重复 success callback 只恢复一次 flow

### Tests to remove or rewrite

- 删除只针对 deferred-ticket 两阶段协议成立的 `prepare/complete` 测试
- 重写页面渲染测试，恢复为“GET 页面直接包含 ticket”

### Manual verification

- 从 HA 添加集成开始，验证 IAR 通过后是否重新恢复到“短信已发送”
- 验证是否不再在 IAR 之后立即出现 `00201`
- 验证 IAR 后输入短信验证码仍能继续进入家庭选择
- 验证关闭 IAR 页面后重新发起配置不会卡在 `already_in_progress`
