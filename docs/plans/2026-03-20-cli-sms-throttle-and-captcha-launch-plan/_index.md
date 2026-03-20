# CLI SMS Throttle And Captcha Launch Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to execute this plan task-by-task.

**Goal:** 为 CLI 登录流程增加短信限流独立提示，并把验证码页改成手动点击后再启动验证。

**Architecture:** 通过在 runtime 层新增 `SmsRateLimitedError` 来区分 `00201`，由 CLI `main()` 输出独立状态；同时把共用 `captcha_bridge` 页面从自动初始化改成按钮触发初始化，保持风险上下文采集与回传逻辑不变。

**Tech Stack:** Python 3.14, requests, 本地 HTTP bridge, pytest

**Design Support:**
- [BDD Specs](../2026-03-20-cli-sms-throttle-and-captcha-launch-design/bdd-specs.md)
- [Architecture](../2026-03-20-cli-sms-throttle-and-captcha-launch-design/architecture.md)
- [Best Practices](../2026-03-20-cli-sms-throttle-and-captcha-launch-design/best-practices.md)

**Execution Plan:**
- [Task 001: SMS Rate Limit Test](./task-001-sms-rate-limit-test.md)
- [Task 001: SMS Rate Limit Impl](./task-001-sms-rate-limit-impl.md)
- [Task 002: Manual Captcha Launch Test](./task-002-manual-captcha-launch-test.md)
- [Task 002: Manual Captcha Launch Impl](./task-002-manual-captcha-launch-impl.md)
- [Task 003: CLI Verification](./task-003-cli-verification.md)

## Constraints

- 只改 `00201` 的错误提示与验证码页启动方式，不顺手改登录协议。
- `src/` 与 vendored runtime 必须同步修改。
- 保留现有风险上下文采集、成功回传与幂等保护。
- 验证优先使用 `tests/test_client.py` 与 `tests/test_captcha_bridge.py`。
