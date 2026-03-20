from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from homeassistant import config_entries
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.suning_biu import async_setup_entry
from custom_components.suning_biu.client_lib import SuningDependencyError, load_client_lib
from custom_components.suning_biu.climate import SuningClimateEntity, async_setup_entry as climate_async_setup_entry
from custom_components.suning_biu.config_flow import SuningConfigFlow
from custom_components.suning_biu.const import (
  CONF_FAMILY_ID,
  CONF_FAMILY_NAME,
  CONF_INTERNATIONAL_CODE,
  CONF_PHONE_NUMBER,
  DOMAIN,
)
from custom_components.suning_biu.coordinator import SuningDataUpdateCoordinator


@dataclass(slots=True)
class FakeConfigEntry:
  data: dict[str, Any]
  entry_id: str = "entry-1"
  runtime_data: Any = None
  state: Any = config_entries.ConfigEntryState.SETUP_IN_PROGRESS

  def async_on_unload(self, _callback: Any) -> None:
    return None


class FakeConfigEntriesManager:
  def __init__(self) -> None:
    self.forwarded: list[tuple[Any, tuple[Any, ...]]] = []

  async def async_forward_entry_setups(self, entry: Any, platforms: tuple[Any, ...]) -> None:
    self.forwarded.append((entry, platforms))

  async def async_unload_platforms(self, entry: Any, platforms: tuple[Any, ...]) -> bool:
    self.forwarded.append((entry, platforms))
    return True


def test_load_client_lib_wraps_runtime_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(
    "custom_components.suning_biu.client_lib._load_client_lib",
    lambda: (_ for _ in ()).throw(ModuleNotFoundError("boom")),
  )

  with pytest.raises(SuningDependencyError, match="runtime dependency is unavailable"):
    load_client_lib()


def test_load_client_lib_uses_vendored_runtime() -> None:
  client_lib = load_client_lib()

  assert client_lib.SuningSmartHomeClient.__module__.startswith(
    "custom_components.suning_biu.suning_biu_ha"
  )
  assert client_lib.LocalCaptchaBridge.__module__.startswith(
    "custom_components.suning_biu.suning_biu_ha"
  )


@pytest.mark.asyncio
async def test_async_setup_entry_ignores_legacy_har_path_and_initializes_client(
  monkeypatch: pytest.MonkeyPatch,
  tmp_path: Path,
) -> None:
  init_calls: list[dict[str, Any]] = []

  class FakeClient:
    def __init__(self, *, state_path: Path, har_path: str | None = None) -> None:
      init_calls.append({"state_path": state_path, "har_path": har_path})
      self.state = SimpleNamespace(phone_number=None, international_code=None)

    def keep_alive(self) -> None:
      return None

    def list_air_conditioner_statuses(self, family_id: str) -> list[object]:
      assert family_id == "37790"
      return [SimpleNamespace(device_id="ac-1")]

  hass = HomeAssistant(str(tmp_path))
  hass.config_entries = FakeConfigEntriesManager()
  entry = FakeConfigEntry(
    data={
      CONF_PHONE_NUMBER: "13800000000",
      CONF_INTERNATIONAL_CODE: "0086",
      "har_path": "captures/missing.har",
      CONF_FAMILY_ID: "37790",
    }
  )

  monkeypatch.setattr(
    "custom_components.suning_biu.load_client_lib",
    lambda: SimpleNamespace(
      SuningSmartHomeClient=FakeClient,
      AuthenticationError=RuntimeError,
      SuningError=RuntimeError,
    ),
  )

  result = await async_setup_entry(hass, entry)

  assert result is True
  assert init_calls[0]["har_path"] is None
  assert init_calls[0]["state_path"] == tmp_path / ".storage" / "suning_biu_0086_13800000000.json"
  assert entry.runtime_data.client.state.phone_number == "13800000000"
  assert entry.runtime_data.client.state.international_code == "0086"


@pytest.mark.asyncio
async def test_coordinator_raises_config_entry_auth_failed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  class AuthenticationError(Exception):
    pass

  class FakeClient:
    def keep_alive(self) -> None:
      raise AuthenticationError("session expired")

    def list_air_conditioner_statuses(self, family_id: str) -> list[object]:
      raise AssertionError(f"should not fetch devices for {family_id}")

  monkeypatch.setattr(
    "custom_components.suning_biu.coordinator.load_client_lib",
    lambda: SimpleNamespace(
      AuthenticationError=AuthenticationError,
      SuningError=RuntimeError,
    ),
  )

  coordinator = SuningDataUpdateCoordinator(
    hass=HomeAssistant(str(tmp_path)),
    config_entry=FakeConfigEntry(data={}),
    client=FakeClient(),
    family_id="37790",
  )

  with pytest.raises(ConfigEntryAuthFailed, match="session expired"):
    await coordinator._async_update_data()  # noqa: SLF001


@pytest.mark.asyncio
async def test_user_step_form_no_longer_contains_har_field(tmp_path: Path) -> None:
  flow = SuningConfigFlow()
  flow.hass = HomeAssistant(str(tmp_path))
  flow.context = {"source": config_entries.SOURCE_USER}

  result = await flow.async_step_user()

  schema = result["data_schema"].schema
  field_names = {field.schema for field in schema}
  assert field_names == {CONF_PHONE_NUMBER, CONF_INTERNATIONAL_CODE}


@pytest.mark.asyncio
async def test_family_step_creates_entry_without_har_path(
  monkeypatch: pytest.MonkeyPatch,
  tmp_path: Path,
) -> None:
  class SuningError(Exception):
    pass

  class FakeClient:
    def list_air_conditioner_statuses(self, family_id: str) -> list[object]:
      assert family_id == "37790"
      return [object()]

  flow = SuningConfigFlow()
  flow.hass = HomeAssistant(str(tmp_path))
  flow.context = {"source": config_entries.SOURCE_USER}
  flow._client = FakeClient()
  flow._phone_number = "13800000000"
  flow._international_code = "0086"
  flow._families = [SimpleNamespace(family_id="37790", name="我的家")]

  monkeypatch.setattr(
    "custom_components.suning_biu.config_flow.load_client_lib",
    lambda: SimpleNamespace(SuningError=SuningError),
  )

  result = await flow.async_step_family({CONF_FAMILY_ID: "37790"})

  assert result["type"] == "create_entry"
  assert result["data"] == {
    CONF_PHONE_NUMBER: "13800000000",
    CONF_INTERNATIONAL_CODE: "0086",
    CONF_FAMILY_ID: "37790",
    CONF_FAMILY_NAME: "我的家",
  }


@pytest.mark.asyncio
async def test_reauth_sms_code_step_updates_existing_entry(
  monkeypatch: pytest.MonkeyPatch,
  tmp_path: Path,
) -> None:
  class SuningError(Exception):
    pass

  class FakeClient:
    def __init__(self) -> None:
      self.login_calls: list[tuple[str, str, str]] = []
      self.keep_alive_called = False

    def login_with_sms_code(
      self,
      *,
      phone_number: str,
      sms_code: str,
      international_code: str,
    ) -> None:
      self.login_calls.append((phone_number, sms_code, international_code))

    def keep_alive(self) -> None:
      self.keep_alive_called = True

  fake_client = FakeClient()
  flow = SuningConfigFlow()
  flow.hass = HomeAssistant(str(tmp_path))
  flow.context = {"source": config_entries.SOURCE_REAUTH}
  flow._client = fake_client
  flow._phone_number = "13800000000"
  flow._international_code = "0086"

  reauth_entry = FakeConfigEntry(
    data={
      CONF_PHONE_NUMBER: "13800000000",
      CONF_INTERNATIONAL_CODE: "0086",
      CONF_FAMILY_ID: "37790",
    }
  )

  monkeypatch.setattr(
    "custom_components.suning_biu.config_flow.load_client_lib",
    lambda: SimpleNamespace(SuningError=SuningError),
  )
  monkeypatch.setattr(flow, "_get_reauth_entry", lambda: reauth_entry)
  monkeypatch.setattr(
    flow,
    "async_update_reload_and_abort",
    lambda entry, **kwargs: {"type": "abort", "reason": "reauth_successful", "entry_id": entry.entry_id},
  )

  result = await flow.async_step_sms_code({"sms_code": "123456"})

  assert result == {"type": "abort", "reason": "reauth_successful", "entry_id": "entry-1"}
  assert fake_client.login_calls == [("13800000000", "123456", "0086")]
  assert fake_client.keep_alive_called is True


@pytest.mark.asyncio
async def test_iar_captcha_step_updates_risk_context_before_retry(
  monkeypatch: pytest.MonkeyPatch,
  tmp_path: Path,
) -> None:
  class SuningError(Exception):
    pass

  class CaptchaRequiredError(Exception):
    def __init__(self, risk_type: str) -> None:
      super().__init__(risk_type)
      self.risk_type = risk_type

  class FakeBridge:
    def __init__(self, *, ticket: str, script_urls: list[str] | None = None) -> None:
      self.ticket = ticket
      self.script_urls = script_urls
      self.url = "http://127.0.0.1:43127/"
      self.started = False
      self.closed = False

    def start(self) -> None:
      self.started = True

    def wait_for_token(self, _timeout: float) -> Any:
      return SimpleNamespace(
        token="iar-token",
        detect="browser-detect",
        dfp_token="browser-dfp",
      )

    def close(self) -> None:
      self.closed = True

  class FakeClient:
    def __init__(self) -> None:
      self.risk_context_script_urls = ["https://example.com/fp.js"]
      self.send_sms_calls: list[tuple[str | None, str | None, Any | None]] = []
      self.risk_updates: list[tuple[str | None, str | None]] = []

    def send_sms_code(
      self,
      phone_number: str,
      *,
      international_code: str | None = None,
      captcha: Any | None = None,
    ) -> None:
      self.send_sms_calls.append(
        (
          getattr(self, "detect", None),
          getattr(self, "dfp_token", None),
          captcha,
        )
      )
      if captcha is None:
        raise CaptchaRequiredError("isIarVerifyCode")

    def request_iar_verify_code_ticket(self, _phone_number: str) -> str:
      return "ticket-123"

    def update_risk_context(self, *, detect: str | None = None, dfp_token: str | None = None) -> None:
      self.detect = detect
      self.dfp_token = dfp_token
      self.risk_updates.append((detect, dfp_token))

  fake_client = FakeClient()
  flow = SuningConfigFlow()
  flow.hass = HomeAssistant(str(tmp_path))
  flow.context = {"source": config_entries.SOURCE_USER}
  flow._client = fake_client
  flow._phone_number = "13800000000"
  flow._international_code = "0086"

  monkeypatch.setattr(
    "custom_components.suning_biu.config_flow.load_client_lib",
    lambda: SimpleNamespace(
      SuningError=SuningError,
      CaptchaRequiredError=CaptchaRequiredError,
      LocalCaptchaBridge=FakeBridge,
      CaptchaSolution=lambda **kwargs: SimpleNamespace(**kwargs),
    ),
  )
  async def fake_async_step_sms_code(*_args, **_kwargs: Any) -> dict[str, Any]:
    return {"type": "form", "step_id": "sms_code"}

  monkeypatch.setattr(flow, "async_step_sms_code", fake_async_step_sms_code)

  captcha_result = await flow._async_send_sms()  # noqa: SLF001
  assert captcha_result["step_id"] == "captcha"
  assert isinstance(flow._captcha_bridge, FakeBridge)
  assert flow._captcha_bridge.script_urls == ["https://example.com/fp.js"]

  result = await flow.async_step_captcha({})

  assert result == {"type": "form", "step_id": "sms_code"}
  assert fake_client.risk_updates == [("browser-detect", "browser-dfp")]
  assert len(fake_client.send_sms_calls) == 2
  assert fake_client.send_sms_calls[1][0:2] == ("browser-detect", "browser-dfp")
  assert fake_client.send_sms_calls[1][2].kind == "iar"
  assert fake_client.send_sms_calls[1][2].value == "iar-token"


def test_climate_entity_exposes_expected_state() -> None:
  status = SimpleNamespace(
    device_id="ac-1",
    name="卧室空调",
    model="KFR-35GW",
    group_name="卧室",
    available=True,
    current_temperature=26.0,
    target_temperature=24.0,
    family_id="37790",
    group_id="group-1",
    summary="在线",
    device_record_time="2026-03-20T00:00:00Z",
    refresh_time="2026-03-20T00:05:00Z",
    mode_raw="3",
    fan_mode_raw="2",
    online=True,
    ha_climate_preview=SimpleNamespace(hvac_mode="off"),
  )
  coordinator = SimpleNamespace(status_for=lambda _device_id: status)
  entry = FakeConfigEntry(data={}, entry_id="entry-1")

  entity = SuningClimateEntity(
    coordinator=coordinator,
    entry=entry,
    device_id="ac-1",
  )

  assert entity.available is True
  assert entity.hvac_modes == [HVACMode.OFF]
  assert entity.hvac_mode == HVACMode.OFF
  assert entity.current_temperature == 26.0
  assert entity.target_temperature == 24.0
  assert entity.device_info["identifiers"] == {(DOMAIN, "ac-1")}
  assert entity.extra_state_attributes[CONF_FAMILY_ID] == "37790"


@pytest.mark.asyncio
async def test_climate_async_setup_entry_adds_one_entity_per_device_id(tmp_path: Path) -> None:
  captured_entities: list[Any] = []
  coordinator = SimpleNamespace(device_ids=("ac-1", "ac-2"))
  entry = FakeConfigEntry(
    data={},
    runtime_data=SimpleNamespace(coordinator=coordinator),
    entry_id="entry-1",
  )

  await climate_async_setup_entry(
    HomeAssistant(str(tmp_path)),
    entry,
    lambda entities: captured_entities.extend(list(entities)),
  )

  assert [entity._device_id for entity in captured_entities] == ["ac-1", "ac-2"]  # noqa: SLF001


def test_strings_json_removes_har_text_and_keeps_reauth() -> None:
  strings_path = Path("custom_components/suning_biu/strings.json")
  payload = json.loads(strings_path.read_text(encoding="utf-8"))

  assert "har_path" not in payload["config"]["step"]["user"]["data"]
  assert "reconfigure" not in payload["config"]["step"]
  assert "har_not_found" not in payload["config"]["error"]
  assert "reauth_confirm" in payload["config"]["step"]
  assert "reauth_successful" in payload["config"]["abort"]
