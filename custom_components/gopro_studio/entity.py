"""Bazowa encja GoPro Studio."""
from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GoProError
from .const import DOMAIN, MANUFACTURER
from .coordinator import GoProCoordinator


class GoProEntity(CoordinatorEntity[GoProCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: GoProCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.info
        self._attr_unique_id = f"{coordinator.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            manufacturer=MANUFACTURER,
            name=info.get("model_name", "GoPro"),
            model=info.get("model_name"),
            model_id=str(info.get("model_number", "")) or None,
            sw_version=info.get("firmware_version"),
            serial_number=coordinator.serial,
        )

    @property
    def api(self):
        return self.coordinator.api

    async def _call(self, coro: Awaitable, refresh: bool = True):
        """Wywołanie API z czytelnym błędem w HA i odświeżeniem stanu."""
        try:
            res = await coro
        except GoProError as err:
            raise HomeAssistantError(f"GoPro: {err}") from err
        if refresh:
            await self.coordinator.async_request_refresh()
        return res
