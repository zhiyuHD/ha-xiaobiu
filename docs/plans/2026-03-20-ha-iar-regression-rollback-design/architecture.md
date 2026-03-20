# Architecture for HA IAR Regression Rollback

## System Overview

这次不是引入新能力，而是把 HA IAR 流程从 deferred-ticket 回退到 eager-ticket。

目标架构保持和 `dbd5806` 一致：

1. `config_flow` 触发短信发送
2. 苏宁返回 `isIarVerifyCode`
3. `config_flow` 立即申请 `iarVerifyCodeTicket`
4. HA 创建带现成 ticket 的 IAR session
5. 浏览器打开 external-step 页面完成拼图
6. 浏览器回传 `token + detect + dfpToken`
7. `captcha_done` 更新风险上下文并重试 `send_sms_code`

## Components

### `SuningConfigFlow`

文件：
- [`custom_components/suning_biu/config_flow.py`](/root/workspace/suning/custom_components/suning_biu/config_flow.py)

职责：
- 创建登录 client
- 捕获 `CaptchaRequiredError`
- 为 IAR 创建 external-step session
- 在 `captcha_done` 中恢复短信发送
- 将底层错误映射回 HA flow 表单

回滚后应保持：
- IAR ticket 在这里申请
- 恢复失败时保留异常日志

### `SuningIARCaptchaView`

文件：
- [`custom_components/suning_biu/iar_external_view.py`](/root/workspace/suning/custom_components/suning_biu/iar_external_view.py)

职责：
- 通过 `flow_id + nonce` 暴露 external-step capability URL
- 渲染验证码页面
- 接收拼图成功后的单次回调
- 调度 `async_configure(flow_id)` 恢复 flow

回滚后应保持：
- 单阶段 POST 模式
- `resume_requested` 幂等保护

### `captcha_bridge` page

文件：
- [`custom_components/suning_biu/suning_biu_ha/captcha_bridge.py`](/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/captcha_bridge.py)
- [`src/suning_biu_ha/captcha_bridge.py`](/root/workspace/suning/src/suning_biu_ha/captcha_bridge.py)

职责：
- 加载苏宁验证码脚本
- 采集浏览器侧 `detect/dfpToken`
- 在成功回调中一次性提交 `token + detect + dfpToken`

回滚后应保持：
- 直接使用服务端提前提供的 `ticket`
- 不承担 ticket 申请职责

## Data Structures

### `IARCaptchaSession`

回滚后的目标字段：

- `flow_id`
- `nonce`
- `ticket`
- `script_urls`
- `env`
- `result`
- `resume_requested`

不再保留：

- `client`
- `phone_number`
- `prepared_detect`
- `prepared_dfp_token`

### `IARCaptchaResult`

保持不变：

- `token`
- `detect`
- `dfp_token`

## Integration Points

### 与 runtime client 的边界

文件：
- [`custom_components/suning_biu/suning_biu_ha/client.py`](/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/client.py)

关键点：

- `request_iar_verify_code_ticket()` 只在 `config_flow` 中调用
- `send_sms_code()` 仍然是恢复发送短信的最终执行边界
- `00201` 这类真实业务错误从 client 抛出，再由 HA flow 记录日志并映射给 UI

### 与浏览器的边界

浏览器只负责：

- 展示已有 ticket 的 IAR 组件
- 采集当前浏览器风控上下文
- 把成功结果一次性回传给 HA

浏览器不负责：

- 决定 ticket 申请时机
- 改写 HA session 状态机

## Technology Choices

- 继续使用现有 Home Assistant external-step 模式，不引入新页面机制
- 继续复用现有 `SnCaptcha.js`、`mmds`、`dfp` 风控脚本
- 继续使用当前 `resume_requested` 幂等保护
- 避免新增一层 `prepare` 协议，减少与苏宁交互时序的不确定性
