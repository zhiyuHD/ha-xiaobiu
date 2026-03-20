# Task 002: Manual Captcha Launch Impl

**depends-on**: task-002-manual-captcha-launch-test

## Description

将共用验证码桥接页从自动初始化改成用户点击后再启动，同时保留风险上下文采集、成功回传和提交幂等保护。

## BDD Scenario

```gherkin
Scenario: 本地 IAR 验证页加载后不自动初始化验证码
  Given 用户在浏览器打开本地验证码页
  When 页面刚刚完成加载且用户还未点击开始按钮
  Then 页面应展示手动开始验证的按钮和说明
  And 页面源码中不应在加载阶段直接执行 SnCaptcha.init
  When 用户点击开始验证
  Then 页面才初始化 SnCaptcha 并继续现有的风险上下文采集与回传逻辑
```

## Files to Modify/Create

- Modify: `/root/workspace/suning/src/suning_biu_ha/captcha_bridge.py`
- Modify: `/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/captcha_bridge.py`

## Verification Commands

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_captcha_bridge.py -q
```
