from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SuningConfigEntry, SuningRuntimeData
from .const import CONF_FAMILY_ID, DOMAIN
from .coordinator import SuningDataUpdateCoordinator


async def async_setup_entry(
  hass: HomeAssistant,
  entry: SuningConfigEntry,
  async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
  runtime_data: SuningRuntimeData = entry.runtime_data
  async_add_entities(
    SuningClimateEntity(
      coordinator=runtime_data.coordinator,
      entry=entry,
      device_id=device_id,
    )
    for device_id in runtime_data.coordinator.device_ids
  )


class SuningClimateEntity(CoordinatorEntity[SuningDataUpdateCoordinator], ClimateEntity):
  _attr_has_entity_name = True
  _attr_translation_key = "suning_air_conditioner"
  _attr_temperature_unit = UnitOfTemperature.CELSIUS
  _attr_target_temperature_step = 1.0
  # 添加支持的功能：开关机和调温度
  _attr_supported_features = (
    ClimateEntityFeature.TURN_ON |
    ClimateEntityFeature.TURN_OFF |
    ClimateEntityFeature.TARGET_TEMPERATURE
  )
  _enable_turn_on_off_backwards_compatibility = False

  def __init__(
    self,
    *,
    coordinator: SuningDataUpdateCoordinator,
    entry: SuningConfigEntry,
    device_id: str,
  ) -> None:
    super().__init__(coordinator)
    self._entry = entry
    self._device_id = device_id
    self._attr_unique_id = f"{entry.entry_id}_{device_id}"

  @property
  def _status(self) -> Any:
    return self.coordinator.status_for(self._device_id)

  @property
  def _model_id(self) -> str | None:
    """获取设备的 model_id，用于控制 API"""
    raw_device = getattr(self._status, "raw_device", None)
    if raw_device:
      return raw_device.get("modelId")
    return None

  @property
  def available(self) -> bool:
    return self._status.available

  @property
  def name(self) -> str | None:
    return None

  @property
  def device_info(self) -> DeviceInfo:
    status = self._status
    return DeviceInfo(
      identifiers={(DOMAIN, status.device_id)},
      name=status.name,
      model=status.model,
      manufacturer="Suning",
      suggested_area=status.group_name,
    )

  @property
  def hvac_modes(self) -> list[HVACMode]:
    # 根据实际设备支持的模式添加
    return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.DRY]
    # 如果你不确定，可以先用 ['off', 'cool'] 测试

  @property
  def hvac_mode(self) -> HVACMode | None:
    """返回当前 HVAC 模式"""
    status = self._status
    # 如果设备关机，返回 OFF
    if not status.power_on:
      return HVACMode.OFF
    
    # 根据 mode_raw 映射到 HVACMode
    # 从抓包数据可知: 1:自动, 2:制冷, 3:制热, 4:送风, 5:除湿
    mode_map = {
      "1": HVACMode.AUTO,
      "2": HVACMode.COOL,
      "3": HVACMode.HEAT,
      "4": HVACMode.FAN_ONLY,
      "5": HVACMode.DRY,
    }
    return mode_map.get(status.mode_raw, HVACMode.COOL)

  @property
  def current_temperature(self) -> float | None:
    return self._status.current_temperature

  @property
  def target_temperature(self) -> float | None:
    return self._status.target_temperature

  @property
  def extra_state_attributes(self) -> dict[str, Any]:
    status = self._status
    return {
      CONF_FAMILY_ID: status.family_id,
      "group_id": status.group_id,
      "group_name": status.group_name,
      "summary": status.summary,
      "device_record_time": status.device_record_time,
      "refresh_time": status.refresh_time,
      "raw_mode": status.mode_raw,
      "raw_fan_mode": status.fan_mode_raw,
      "online": status.online,
    }

  # ========== 控制方法 ==========

  async def async_turn_on(self) -> None:
    """开机"""
    if not self._model_id:
      return
    await self.hass.async_add_executor_job(
      self.coordinator.client.set_air_conditioner_power,
      self._device_id,
      self._model_id,
      True,
    )
    # 控制成功后刷新状态
    await self.coordinator.async_request_refresh()

  async def async_turn_off(self) -> None:
    """关机"""
    if not self._model_id:
      return
    await self.hass.async_add_executor_job(
      self.coordinator.client.set_air_conditioner_power,
      self._device_id,
      self._model_id,
      False,
    )
    await self.coordinator.async_request_refresh()

  async def async_set_temperature(self, **kwargs) -> None:
    """设置目标温度"""
    temperature = kwargs.get("temperature")
    if temperature is None:
      return
    if not self._model_id:
      return
    await self.hass.async_add_executor_job(
      self.coordinator.client.set_air_conditioner_temperature,
      self._device_id,
      self._model_id,
      temperature,
    )
    await self.coordinator.async_request_refresh()

  async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    """设置 HVAC 模式（制冷/制热/送风/除湿/自动）"""
    if not self._model_id:
      return
    
    # 先开机（如果当前是关机状态）
    if not self._status.power_on:
      await self.async_turn_on()
    
    # 映射 HVACMode 到苏宁的 mode_raw 值
    # 1:自动, 2:制冷, 3:制热, 4:送风, 5:除湿
    mode_map = {
      HVACMode.AUTO: "1",
      HVACMode.COOL: "2",
      HVACMode.HEAT: "3",
      HVACMode.FAN_ONLY: "4",
      HVACMode.DRY: "5",
    }
    mode_raw = mode_map.get(hvac_mode)
    if not mode_raw:
      return
    
    await self.hass.async_add_executor_job(
      self.coordinator.client.control_air_conditioner,
      self._device_id,
      self._model_id,
      {"SN_MODE": mode_raw},
    )
    await self.coordinator.async_request_refresh()