# Best Practices for HA IAR Regression Rollback

## Security Considerations

- 继续把 external-step URL 限制在 `flow_id + nonce` 一次性 capability 模式，不扩大暴露面。
- 不在日志中输出手机号、验证码 token、`detect`、`dfpToken` 的原文。
- 保留恢复失败日志时，只记录 flow 级别上下文和异常摘要，不记录敏感风控载荷。

## Performance Considerations

- 回滚 `prepare` 阶段后，浏览器少一次额外 HTTP 往返，页面初始化更简单。
- `resume_requested` 幂等保护必须保留，避免浏览器重复回调导致多次 `async_configure(flow_id)`。
- 风控脚本加载和 `detect/dfpToken` 轮询逻辑不应被回滚掉，否则会重新引入 IAR 循环问题。

## Code Quality

- 回滚只针对 `1b72b07` 引入的协议时序改动，不顺手改其他登录链路。
- `src/` runtime 与 vendored runtime 继续保持同步；这次回滚虽然主要发生在 HA 侧，但共享桥接页文件仍要同步更新。
- 测试要围绕行为回归，而不是围绕实现细节写断言。

## Common Pitfalls

- 不要因为 `ha6.har` 里看见“回调成功后 `cannot_connect`”就再次把前端现象当成根因。
- 不要保留半套 deferred-ticket 代码；如果决定回滚，就把 `prepare` 状态和相关测试一起移除。
- 不要回滚掉已经有价值的日志增强，否则下次仍会只剩模糊的 `cannot_connect`。
- 不要破坏已经修好的能力：
  - external-step session 生命周期
  - 关闭页面后重新发起 flow 的接管逻辑
  - 风险上下文采集与重复 success callback 幂等保护

## Verification Notes

- 自动化验证主要证明“行为契约已经回到 eager-ticket 模型”。
- 真正的验收仍要靠 HA 手工复测：
  - IAR 后是否能请求短信
  - 输入短信码后是否还能继续到家庭选择
  - 是否没有重复弹页或卡住旧 flow
