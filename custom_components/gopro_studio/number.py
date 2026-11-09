"""Zoom cyfrowy."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ST_ZOOM, ST_ZOOM_AVAILABLE
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([ZoomNumber(entry.runtime_data.coordinator, "zoom")])


class ZoomNumber(GoProEntity, NumberEntity):
    _attr_translation_key = "zoom"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    @property
    def available(self) -> bool:
        # status 77: zoom cyfrowy dostępny w bieżącym trybie/obiektywie
        return super().available and bool(self.coordinator.status(ST_ZOOM_AVAILABLE, 1))

    @property
    def native_value(self):
        return self.coordinator.status(ST_ZOOM)

    async def async_set_native_value(self, value: float) -> None:
        await self._call(self.api.zoom(int(value)))
