from __future__ import annotations

import json
from urllib.request import Request, urlopen

from suning_biu_ha.captcha_bridge import LocalCaptchaBridge


def test_local_captcha_bridge_serves_ticket_and_accepts_callback() -> None:
  bridge = LocalCaptchaBridge(ticket="ticket-123")
  bridge.start()
  try:
    with urlopen(bridge.url) as response:
      html = response.read().decode("utf-8")
    assert "ticket-123" in html
    assert "SnCaptcha.init" in html
    assert "align-items: flex-start" in html
    assert "computeCaptchaSize" in html
    assert "window.__RISK_CONTEXT_SCRIPT_URLS__" in html
    assert "mmds.suning.com/mmds/mmds.js" in html

    request = Request(
      bridge.url + "callback",
      data=json.dumps(
        {
          "token": "token-456",
          "detect": "browser-detect",
          "dfpToken": "browser-dfp",
        }
      ).encode("utf-8"),
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    with urlopen(request) as response:
      body = response.read().decode("utf-8")
    assert json.loads(body) == {"ok": True}

    result = bridge.wait_for_token(timeout=0.5)
    assert result.token == "token-456"
    assert result.detect == "browser-detect"
    assert result.dfp_token == "browser-dfp"
  finally:
    bridge.close()
