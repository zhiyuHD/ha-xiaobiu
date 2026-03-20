# Architecture

- `send_sms_code()` 继续负责解析 `sendCode.do` 的业务响应，但在识别到 `00201` 时抛出独立的 `SmsRateLimitedError`，而不是复用泛化 `SuningError`。
- CLI `main()` 单独捕获 `SmsRateLimitedError`，输出可机器识别的 `status` 和面向用户的重试提示。
- `render_captcha_page()` 改成显式的手动启动模型：
  - 初始状态只渲染说明文字与“开始验证”按钮
  - 用户点击后才调用 `SnCaptcha.init(...)`
  - 风险上下文采集、成功回传、幂等保护保持现有实现
- `src/` 与 vendored 副本必须同步，避免 CLI 与 HA runtime 再次出现行为漂移。
