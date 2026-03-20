# Task 001: SMS Rate Limit Impl

**depends-on**: task-001-sms-rate-limit-test

## Description

在 shared runtime 中新增短信限流错误分类，并让 CLI `main()` 输出独立状态与重试提示。

## BDD Scenario

```gherkin
Scenario: sendCode 返回短信发送频繁错误
  Given CLI 已经完成 IAR 验证并准备重试发送短信
  When 苏宁 sendCode 接口返回 "验证码发送失败，请稍后重试(00201)"
  Then runtime 应抛出可区分的短信限流错误
  And CLI 输出中应包含独立的 status 和更明确的重试提示
```

## Files to Modify/Create

- Modify: `/root/workspace/suning/src/suning_biu_ha/client.py`
- Modify: `/root/workspace/suning/src/suning_biu_ha/__init__.py`
- Modify: `/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/client.py`
- Modify: `/root/workspace/suning/custom_components/suning_biu/suning_biu_ha/__init__.py`

## Verification Commands

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_client.py -q -k "rate_limit or sms_rate_limited"
```
