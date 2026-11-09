"""Listy wyboru: tryb, preset oraz WSZYSTKIE ustawienia kamery (schemat z /gp/gpControl)."""
from __future__ import annotations

from collections import Counter

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import GoProError
from .const import DOMAIN, GROUP_OPTIONS, SETTING_NAME_OVERRIDES, PRIMARY_SETTINGS, ST_GROUP, ST_PRESET
from .coordinator import GoProCoordinator
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord: GoProCoordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = [ModeSelect(coord, "mode"), PresetSelect(coord, "preset")]
    present = {int(k) for k in (coord.data or {}).get("settings", {})}
    sids = [s for s in sorted(present)
            if coord.schema_settings.get(s, {}).get("options") and s not in coord.hidden_settings]
    base = {s: SETTING_NAME_OVERRIDES.get(s, coord.schema_settings[s]["display_name"]) for s in sids}
    sec = coord.setting_section
    counts = Counter((sec.get(s), base[s]) for s in sids)
    named = {}
    for sid in sids:
        name = base[sid]
        if counts[(sec.get(sid), name)] > 1 and coord.setting_category.get(sid):
            name = f"{name} ({coord.setting_category[sid]})"
        named[sid] = name
    counts = Counter((sec.get(s), named[s]) for s in sids)
    for sid in sids:
        name = named[sid] if counts[(sec.get(sid), named[sid])] == 1 else f"{named[sid]} #{sid}"
        entities.append(SettingSelect(coord, sid, name))
    # usuń encje ustawień, których już nie tworzymy (np. ustawienia transmisji)
    reg = er.async_get(hass)
    for sid in coord.hidden_settings:
        if old := reg.async_get_entity_id("select", DOMAIN, f"{coord.serial}_setting_{sid}"):
            reg.async_remove(old)
    async_add_entities(entities)


class ModeSelect(GoProEntity, SelectEntity):
    _attr_translation_key = "mode"
    _attr_options = list(GROUP_OPTIONS.values())

    @property
    def current_option(self):
        return GROUP_OPTIONS.get(self.coordinator.status(ST_GROUP))

    async def async_select_option(self, option: str) -> None:
        gid = next(k for k, v in GROUP_OPTIONS.items() if v == option)
        await self._call(self.api.set_group(gid))


class PresetSelect(GoProEntity, SelectEntity):
    """Presety zapisane w kamerze dla aktywnego trybu (także własne)."""

    _attr_translation_key = "preset"

    def _list(self) -> list[tuple[int, str]]:
        lst = self.coordinator.presets.get(self.coordinator.status(ST_GROUP), [])
        out, seen = [], Counter()
        for pid, name in lst:
            seen[name] += 1
            out.append((pid, name if seen[name] == 1 else f"{name} ({pid})"))
        return out

    @property
    def options(self) -> list[str]:
        return [n for _, n in self._list()] or ["—"]

    @property
    def current_option(self):
        cur = self.coordinator.status(ST_PRESET)
        return next((n for pid, n in self._list() if pid == cur), None)

    async def async_select_option(self, option: str) -> None:
        pid = next((p for p, n in self._list() if n == option), None)
        if pid is None:
            raise HomeAssistantError(f"Unknown preset {option}")
        await self._call(self.api.load_preset(pid))


class SettingSelect(GoProEntity, SelectEntity):
    """Jedno ustawienie kamery; opcje filtrowane regułami kamery (tylko dozwolone w danej konfiguracji)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GoProCoordinator, sid: int, name: str) -> None:
        super().__init__(coordinator, f"setting_{sid}", coordinator.setting_section.get(sid))
        self.sid = sid
        self._attr_name = name
        self._attr_entity_registry_enabled_default = sid in PRIMARY_SETTINGS
        self._attr_icon = "mdi:tune-variant"

    @property
    def available(self) -> bool:
        return (super().available and self.coordinator.setting(self.sid) is not None
                and self.coordinator.setting_applies(self.sid))

    @property
    def options(self) -> list[str]:
        return [lbl for _, lbl in self.coordinator.allowed_options(self.sid)]

    @property
    def current_option(self):
        cur = self.coordinator.setting(self.sid)
        return next((lbl for oid, lbl in self.coordinator.allowed_options(self.sid) if oid == cur), None)

    @property
    def extra_state_attributes(self):
        return {"setting_id": self.sid, "option_id": self.coordinator.setting(self.sid),
                "section": self.coordinator.setting_section.get(self.sid),
                "category": self.coordinator.setting_category.get(self.sid),
                "locked_by": self.coordinator.locked_by(self.sid) or None}

    async def async_select_option(self, option: str) -> None:
        oid = next((o for o, lbl in self.coordinator.allowed_options(self.sid) if lbl == option), None)
        if oid is None:
            raise HomeAssistantError(f"Option {option} is not allowed in the current configuration")
        try:
            await self.api.set_setting(self.sid, oid)
        except GoProError as err:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="option_rejected",
                                     translation_placeholders={"setting": str(self.name or ""), "option": option,
                                                               "error": str(err)}) from err
        await self.coordinator.async_request_refresh()
