# BDD Specs

## Scenario 1: CLI 明确提示短信发送过于频繁

```gherkin
Scenario: sendCode 返回短信发送频繁错误
  Given CLI 已经完成 IAR 验证并准备重试发送短信
  When 苏宁 sendCode 接口返回 "验证码发送失败，请稍后重试(00201)"
  Then runtime 应抛出可区分的短信限流错误
  And CLI 输出中应包含独立的 status 和更明确的重试提示
```

## Scenario 2: 验证码页要求手动启动

```gherkin
Scenario: 本地 IAR 验证页加载后不自动初始化验证码
  Given 用户在浏览器打开本地验证码页
  When 页面刚刚完成加载且用户还未点击开始按钮
  Then 页面应展示手动开始验证的按钮和说明
  And 页面源码中不应在加载阶段直接执行 SnCaptcha.init
  When 用户点击开始验证
  Then 页面才初始化 SnCaptcha 并继续现有的风险上下文采集与回传逻辑
```
