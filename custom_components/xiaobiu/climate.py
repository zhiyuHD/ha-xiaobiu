"""Climate platform for Suning XiaoBiu air conditioners."""

from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SuningConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Suning climate entities from a config entry."""
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
    """Suning XiaoBiu air conditioner climate entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "suning_air_conditioner"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = 16
    _attr_max_temp = 31
    
    # 支持的功能：开关机、调温度
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
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = device_id
        self._attr_unique_id = f"{entry.entry_id}_{device_id}"
        self._cached_model_id: str | None = None
        self._model_id_fetched: bool = False

    @property
    def _status(self) -> Any:
        """Return the device status."""
        return self.coordinator.status_for(self._device_id)

    @property
    def _model_id(self) -> str | None:
        """Get model_id for control API.
        
        Tries multiple sources in order of preference:
        1. Cached value from previous fetch
        2. raw_device from status (if available)
        3. Direct API call to list_devices
        4. From entry data (if stored during setup)
        """
        # 1. Return cached value if already fetched
        if self._model_id_fetched:
            return self._cached_model_id
        
        # 2. Try to get from status.raw_device
        raw_device = getattr(self._status, "raw_device", None)
        if raw_device:
            model_id = raw_device.get("modelId") or raw_device.get("model")
            if model_id:
                self._cached_model_id = model_id
                self._model_id_fetched = True
                _LOGGER.debug("Got model_id from raw_device: %s", model_id)
                return model_id
        
        # 3. Try to get from coordinator's device cache
        if hasattr(self.coordinator, "device_cache"):
            device_info = self.coordinator.device_cache.get(self._device_id)
            if device_info:
                model_id = device_info.get("modelId") or device_info.get("model")
                if model_id:
                    self._cached_model_id = model_id
                    self._model_id_fetched = True
                    _LOGGER.debug("Got model_id from device_cache: %s", model_id)
                    return model_id
        
        # 4. Direct API call to list_devices (fallback)
        try:
            family_id = self._entry.data.get(CONF_FAMILY_ID)
            if family_id:
                _LOGGER.debug("Fetching device list to get model_id for %s", self._device_id)
                devices_response = self.coordinator.client.list_devices(family_id)
                devices = devices_response.get("responseData", {}).get("devices", [])
                for device in devices:
                    if device.get("id") == self._device_id:
                        model_id = device.get("modelId") or device.get("model")
                        if model_id:
                            self._cached_model_id = model_id
                            self._model_id_fetched = True
                            # Cache to coordinator for other entities
                            if not hasattr(self.coordinator, "device_cache"):
                                self.coordinator.device_cache = {}
                            self.coordinator.device_cache[self._device_id] = device
                            _LOGGER.debug("Got model_id from API: %s", model_id)
                            return model_id
        except Exception as e:
            _LOGGER.warning("Failed to fetch model_id from API: %s", e)
        
        # 5. Could not get model_id
        _LOGGER.warning("Unable to get model_id for device %s", self._device_id)
        return None

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._status.available

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
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
        """Return the list of available HVAC modes."""
        return [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.FAN_ONLY,
            HVACMode.DRY,
            HVACMode.AUTO,
        ]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        status = self._status
        if not status.power_on:
            return HVACMode.OFF
        
        # mode_raw: 1=自动, 2=制冷, 3=制热, 4=送风, 5=除湿
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
        """Return the current temperature."""
        return self._status.current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._status.target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
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

    # ========== Control Methods ==========

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        model_id = self._model_id
        if not model_id:
            _LOGGER.error("Cannot turn on: model_id is None")
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_air_conditioner_power,
            self._device_id,
            model_id,
            True,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the device off."""
        model_id = self._model_id
        if not model_id:
            _LOGGER.error("Cannot turn off: model_id is None")
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_air_conditioner_power,
            self._device_id,
            model_id,
            False,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        model_id = self._model_id
        if not model_id:
            _LOGGER.error("Cannot set temperature: model_id is None")
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_air_conditioner_temperature,
            self._device_id,
            model_id,
            temperature,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to: %s", hvac_mode)
        
        model_id = self._model_id
        if not model_id:
            _LOGGER.error("Cannot set mode: model_id is None")
            return
        
        # If turning off
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        
        # Ensure device is on
        if not self._status.power_on:
            await self.async_turn_on()
        
        # Map HVACMode to Suning mode_raw values
        # 1=自动, 2=制冷, 3=制热, 4=送风, 5=除湿
        mode_map = {
            HVACMode.AUTO: "1",
            HVACMode.COOL: "2",
            HVACMode.HEAT: "3",
            HVACMode.FAN_ONLY: "4",
            HVACMode.DRY: "5",
        }
        mode_raw = mode_map.get(hvac_mode)
        if not mode_raw:
            _LOGGER.warning("Unknown HVAC mode: %s", hvac_mode)
            return
        
        _LOGGER.debug("Sending mode command: SN_MODE=%s", mode_raw)
        await self.hass.async_add_executor_job(
            self.coordinator.client.control_air_conditioner,
            self._device_id,
            model_id,
            {"SN_MODE": mode_raw},
        )
        await self.coordinator.async_request_refresh()