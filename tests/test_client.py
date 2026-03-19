from __future__ import annotations

import json

from suning_biu_ha import SuningSmartHomeClient, parse_jsonp_or_json
from suning_biu_ha.client import (
  CaptchaSolution,
  DEVICE_LIST_URL,
  FAMILY_LIST_URL,
  SignedRequestTemplate,
  _build_parser,
  _captcha_kind_from_risk_type,
  parse_login_page_config,
)

SAMPLE_LOGIN_PAGE = """
<script>
var loginPBK="LOGIN_PBK";
var rdsyKey="RDSY_KEY";
var ssojbossConstant = {
  rdsyAppCode:"APP_CODE",
  stepFlag:"STEP_ONE",
  stepTwoFlag:"STEP_TWO",
  rdsySceneId:"PASSPORT",
  rdsySceneIdYGHK:"PASSPORT_YGHK",
  stepThreeFlag:"STEP_THREE",
  channel:"PC",
  checkAccountKey: "CHECK_ACCOUNT_KEY"
};
</script>
"""


def test_parse_login_page_config() -> None:
  config = parse_login_page_config(SAMPLE_LOGIN_PAGE)
  assert config.rdsy_app_code == "APP_CODE"
  assert config.step_two_flag == "STEP_TWO"
  assert config.check_account_key == "CHECK_ACCOUNT_KEY"


def test_parse_jsonp_or_json_supports_both_formats() -> None:
  assert parse_jsonp_or_json('{"code":"0"}') == {"code": "0"}
  assert parse_jsonp_or_json('smsLogin({"code":"0"})') == {"code": "0"}


def test_state_file_roundtrip(tmp_path) -> None:
  state_path = tmp_path / "session.json"
  client = SuningSmartHomeClient(state_path=state_path)
  client.state.phone_number = "13800000000"
  client.state.sms_ticket = "SMS_TICKET"
  client.session.cookies.set("authId", "cookie-value", domain=".suning.com", path="/")
  client.save_state()

  reloaded = SuningSmartHomeClient(state_path=state_path)
  assert reloaded.state.phone_number == "13800000000"
  assert reloaded.state.sms_ticket == "SMS_TICKET"
  assert reloaded.session.cookies.get("authId", domain=".suning.com", path="/") == "cookie-value"


def test_captcha_field_mapping() -> None:
  client = SuningSmartHomeClient()
  fields = client._captcha_fields(CaptchaSolution("iar", "token"))  # noqa: SLF001
  assert fields["uuid"] == "iarVerifyCode"
  assert fields["code"] == "token"


def test_login_cli_allows_interactive_sms_code() -> None:
  parser = _build_parser()
  args = parser.parse_args(["login", "--phone", "13800000000"])
  assert args.command == "login"
  assert args.phone == "13800000000"
  assert args.sms_code is None


def test_cli_allows_shared_options_after_subcommand() -> None:
  parser = _build_parser()
  args = parser.parse_args(["families", "--har-file", "sample.har"])
  assert args.command == "families"
  assert args.har_file == "sample.har"


def test_risk_type_to_captcha_kind_mapping() -> None:
  assert _captcha_kind_from_risk_type("isIarVerifyCode") == "iar"
  assert _captcha_kind_from_risk_type("isSlideVerifyCode") == "slide"
  assert _captcha_kind_from_risk_type("isImgVerifyCode") == "image"
  assert _captcha_kind_from_risk_type("unknown") is None


def test_signed_request_template_refreshes_trace_headers() -> None:
  template = SignedRequestTemplate(
    method="POST",
    url=FAMILY_LIST_URL,
    headers={
      "snTraceId": "old-trace",
      "hiro_trace_id": "old-trace",
      "requestTime": "1773960376923",
      "gsSign": "family-sign",
    },
  )

  headers = template.build_headers()

  assert headers["requestTime"] == "1773960376923"
  assert headers["gsSign"] == "family-sign"
  assert headers["snTraceId"] != "old-trace"
  assert headers["hiro_trace_id"] == headers["snTraceId"]


def test_client_loads_signed_templates_from_har(tmp_path) -> None:
  har_path = tmp_path / "signed.har"
  har_payload = {
    "log": {
      "entries": [
        {
          "request": {
            "method": "POST",
            "url": FAMILY_LIST_URL,
            "headers": [
              {"name": "TerminalVersion", "value": "SmartHome/6.4.5"},
              {"name": "hiro_trace_id", "value": "trace-family"},
              {"name": "snTraceId", "value": "trace-family"},
              {"name": "gsSign", "value": "family-sign"},
              {"name": "requestTime", "value": "1773960376923"},
              {"name": "terminalType", "value": "SHCSS_IOS"},
              {"name": "snTraceType", "value": "SDK"},
              {"name": "User-Agent", "value": "SmartHome/6.4.5"},
              {"name": "Content-Type", "value": "application/json"},
            ],
          },
          "response": {
            "status": 200,
            "content": {
              "text": json.dumps({"responseCode": "0", "responseMsg": "SUCCESS"}),
            },
          },
        },
        {
          "request": {
            "method": "POST",
            "url": DEVICE_LIST_URL,
            "headers": [
              {"name": "TerminalVersion", "value": "SmartHome/6.4.5"},
              {"name": "hiro_trace_id", "value": "trace-device"},
              {"name": "snTraceId", "value": "trace-device"},
              {"name": "gsSign", "value": "device-sign"},
              {"name": "requestTime", "value": "1773960378601"},
              {"name": "terminalType", "value": "SHCSS_IOS"},
              {"name": "snTraceType", "value": "SDK"},
              {"name": "User-Agent", "value": "SmartHome/6.4.5"},
              {"name": "Content-Type", "value": "application/json"},
            ],
            "postData": {
              "mimeType": "application/json",
              "text": '{\n  "familyId" : "37790"\n}',
            },
          },
          "response": {
            "status": 200,
            "content": {
              "text": json.dumps({"responseCode": "0", "responseMsg": "SUCCESS"}),
            },
          },
        },
      ]
    }
  }
  har_path.write_text(json.dumps(har_payload), encoding="utf-8")

  client = SuningSmartHomeClient(har_path=har_path)

  family_template = client._find_signed_template("POST", FAMILY_LIST_URL, "")  # noqa: SLF001
  device_template = client._find_signed_template(  # noqa: SLF001
    "POST",
    DEVICE_LIST_URL,
    '{"familyId":"37790"}',
  )

  assert family_template is not None
  assert family_template.headers["gsSign"] == "family-sign"
  assert device_template is not None
  assert device_template.headers["gsSign"] == "device-sign"
  assert client.available_device_template_family_ids() == ["37790"]
