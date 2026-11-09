"""Pole tekstowe "Komenda Labs" - wpisana wartość jest od razu wysyłana do kamery (GoPro Labs przez Wi-Fi)."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EVENT_LABS_SENT
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([LabsCommandText(entry.runtime_data.coordinator, "labs_command")])


class LabsCommandText(GoProEntity, TextEntity):
    _attr_translation_key = "labs_command"
    _attr_native_max = 255
    _attr_icon = "mdi:flask-outline"

    def __init__(self, coordinator, key) -> None:
        super().__init__(coordinator, key)
        self._last = ""

    @property
    def native_value(self) -> str:
        return self._last

    async def async_set_value(self, value: str) -> None:
        value = value.strip()
        if not value:
            return
        await self._call(self.api.labs(value))
        self._last = value
        self.hass.bus.async_fire(EVENT_LABS_SENT, {"camera": self.coordinator.serial, "command": value})
        self.async_write_ha_state()
