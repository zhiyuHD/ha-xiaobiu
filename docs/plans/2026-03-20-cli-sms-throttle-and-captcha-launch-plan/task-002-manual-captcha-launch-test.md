# Task 002: Manual Captcha Launch Test

## Description

把验证码桥接页测试改成手动启动模型：页面加载后必须先看到按钮和说明，且不应在初始 HTML 中自动启动验证码。

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

- Modify: `/root/workspace/suning/tests/test_captcha_bridge.py`

## Verification Commands

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_captcha_bridge.py -q
```
