# suning-biu-ha

Python client for Suning SMS login and smart home session reuse.

## What is implemented

- Parse the Suning login page at runtime to extract the current RSA public keys and flow constants.
- Reproduce `needVerifyCode.do` and `sendCode.do` using Suning's `SuAES` scheme.
- Reproduce `ids/smartLogin/sms` using the RSA-encrypted phone number flow.
- Persist cookies and auth state into a local JSON state file.
- Re-bootstrap `shcss` and `itapig` service sessions after login.
- Verify the session by calling member info, family list, and device list endpoints.
- Reuse signed app-request templates extracted from HAR files for the current `families` / `devices` MVP.
- Normalize AC device payloads into a more stable status model and provide a Home Assistant climate preview.

## Important limits

- When Suning returns `isIarVerifyCode`, the CLI now starts a local bridge page and prints a local URL for the user to open in a browser. After the puzzle is completed, the token is posted back to the local process automatically.
- Other captcha types are not yet fully bridged. If Suning returns a non-IAR captcha, a token still needs to be provided manually.
- If the server insists on real browser fingerprints, pass `--detect` and `--dfp-token` explicitly.
- The smart-home app APIs currently still require HAR-derived signed request templates. By default the client scans `*.har` in the current directory, or you can pass `--har-file`.
- `devices --family-id` can only work for family IDs that already have a matching signed request template in the HAR.
- By default the client uses the same fallback values that Suning's own web page sends when its JS fingerprint code fails:
  - `passport_detect_js_is_error`
  - `passport_dfpToken_js_is_error`

## Install

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv sync --dev
```

## CLI

Interactive login flow:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run main.py login \
  --phone 13800000000 \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har
```

If the server asks for IAR puzzle verification, the terminal will print a local link such as:

```bash
http://127.0.0.1:43127/
```

Open that link in a browser, finish the puzzle, then return to the terminal and enter the SMS code when prompted.

Send an SMS code only:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run main.py send-sms \
  --phone 13800000000 \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har
```

Check whether the session is still valid:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run main.py check \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har
```

List families and devices:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run main.py families \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har

env UV_CACHE_DIR=/tmp/uv-cache uv run main.py devices \
  --family-id 37790 \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har

env UV_CACHE_DIR=/tmp/uv-cache uv run main.py device-status \
  --family-id 37790 \
  --device-id 000165f9b029afa2e5d8 \
  --state-file .suning-session.json \
  --har-file apm.suning.cn_2026_03_19_23_47_23.har

env UV_CACHE_DIR=/tmp/uv-cache uv run main.py device-status \
  --family-id 37790 \
  --raw
```

## Library usage

```python
from suning_biu_ha import CaptchaRequiredError, SuningSmartHomeClient

client = SuningSmartHomeClient(state_path=".suning-session.json")

try:
  client.send_sms_code("13800000000")
except CaptchaRequiredError as error:
  print(error.risk_type, error.sms_ticket)

client.login_with_sms_code(phone_number="13800000000", sms_code="123456")
print(client.list_families())
```
