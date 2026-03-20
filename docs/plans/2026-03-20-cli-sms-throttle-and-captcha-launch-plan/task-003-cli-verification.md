# Task 003: CLI Verification

**depends-on**: task-001-sms-rate-limit-impl, task-002-manual-captcha-launch-impl

## Description

运行针对性回归，确认短信限流提示和手动启动验证码页都已落地，且 vendored/runtime 副本一致。

## BDD Scenario

```gherkin
Scenario: sendCode 返回短信发送频繁错误
  Given CLI 已经完成 IAR 验证并准备重试发送短信
  When 苏宁 sendCode 接口返回 "验证码发送失败，请稍后重试(00201)"
  Then runtime 应抛出可区分的短信限流错误
  And CLI 输出中应包含独立的 status 和更明确的重试提示

Scenario: 本地 IAR 验证页加载后不自动初始化验证码
  Given 用户在浏览器打开本地验证码页
  When 页面刚刚完成加载且用户还未点击开始按钮
  Then 页面应展示手动开始验证的按钮和说明
  And 页面源码中不应在加载阶段直接执行 SnCaptcha.init
```

## Files to Modify/Create

- Modify: `/root/workspace/suning/tasks/todo.md`
- Modify: `/root/workspace/suning/tasks/lessons.md`

## Verification Commands

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_client.py tests/test_captcha_bridge.py -q

env UV_CACHE_DIR=/tmp/uv-cache uv run python -m compileall src/suning_biu_ha custom_components/suning_biu/suning_biu_ha tests

diff -u src/suning_biu_ha/captcha_bridge.py custom_components/suning_biu/suning_biu_ha/captcha_bridge.py

diff -u src/suning_biu_ha/client.py custom_components/suning_biu/suning_biu_ha/client.py
```
