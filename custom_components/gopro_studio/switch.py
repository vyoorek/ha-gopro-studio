"""Przełączniki GoPro Studio: nagrywanie, keep-alive, turbo transfer, sterowanie zewnętrzne."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_KEEP_ALIVE, ST_CONTROL, ST_ENCODING, ST_TURBO
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities([RecordSwitch(coord, "record"), KeepAliveSwitch(coord, "keep_alive_switch"),
                        TurboSwitch(coord, "turbo"), ExternalControlSwitch(coord, "external_control")])


class RecordSwitch(GoProEntity, SwitchEntity):
    _attr_translation_key = "record"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.status(ST_ENCODING))

    async def async_turn_on(self, **kwargs) -> None:
        await self._call(self.api.shutter(True))

    async def async_turn_off(self, **kwargs) -> None:
        await self._call(self.api.shutter(False))


class KeepAliveSwitch(GoProEntity, SwitchEntity):
    """Wysyła keep-alive co kilka sekund, żeby kamera nie zasnęła."""

    _attr_translation_key = "keep_alive"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return self.coordinator.keep_alive_enabled

    async def _set(self, value: bool) -> None:
        entry = self.coordinator.config_entry
        # zmiana opcji przeładowuje wpis - to celowe, koordynator czyta opcje przy starcie
        self.hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_KEEP_ALIVE: value})

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)


class TurboSwitch(GoProEntity, SwitchEntity):
    _attr_translation_key = "turbo"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.status(ST_TURBO))

    async def async_turn_on(self, **kwargs) -> None:
        await self._call(self.api.turbo(True))

    async def async_turn_off(self, **kwargs) -> None:
        await self._call(self.api.turbo(False))


class ExternalControlSwitch(GoProEntity, SwitchEntity):
    """Blokuje ekran i przyciski kamery - steruje wyłącznie HA."""

    _attr_translation_key = "external_control"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return self.coordinator.status(ST_CONTROL) == 2

    async def async_turn_on(self, **kwargs) -> None:
        await self._call(self.api.external_control(True))

    async def async_turn_off(self, **kwargs) -> None:
        await self._call(self.api.external_control(False))
