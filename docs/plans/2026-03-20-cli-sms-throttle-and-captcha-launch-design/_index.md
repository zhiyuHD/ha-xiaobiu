# CLI SMS Throttle And Captcha Launch Design

**Goal:** 改进 CLI 登录体验：把短信发送限流错误 `00201` 暴露成独立、可操作的提示；把 IAR 验证页从“页面加载即初始化验证码”改成“用户手动点击后再开始验证”。

**User Impact:**
- 当苏宁因为发送过于频繁而拒绝短信请求时，CLI 不再只输出泛化错误，而是明确提示稍后再试。
- 打开本地验证码页后，不会立刻自动拉起验证码流程，避免页面一加载就弹出验证。

**Scope:**
- CLI runtime `src/suning_biu_ha/client.py`
- Vendored runtime `custom_components/suning_biu/suning_biu_ha/client.py`
- CLI/HA 共用验证码页 `src/suning_biu_ha/captcha_bridge.py`
- Vendored 验证码页 `custom_components/suning_biu/suning_biu_ha/captcha_bridge.py`
- 回归测试 `tests/test_client.py`、`tests/test_captcha_bridge.py`

**Design Support:**
- [BDD Specs](./bdd-specs.md)
- [Architecture](./architecture.md)
- [Best Practices](./best-practices.md)
