# Task 001: SMS Rate Limit Test

## Description

为短信发送频率限制场景补红灯测试，明确 `00201` 需要走独立错误类型和 CLI 提示，而不是泛化 `SuningError`。

## BDD Scenario

```gherkin
Scenario: sendCode 返回短信发送频繁错误
  Given CLI 已经完成 IAR 验证并准备重试发送短信
  When 苏宁 sendCode 接口返回 "验证码发送失败，请稍后重试(00201)"
  Then runtime 应抛出可区分的短信限流错误
  And CLI 输出中应包含独立的 status 和更明确的重试提示
```

## Files to Modify/Create

- Modify: `/root/workspace/suning/tests/test_client.py`

## Verification Commands

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_client.py -q -k "rate_limit or sms_rate_limited"
```
