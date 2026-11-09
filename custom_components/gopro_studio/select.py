"""Listy wyboru: tryb, preset oraz WSZYSTKIE ustawienia kamery (schemat z /gp/gpControl)."""
from __future__ import annotations

from collections import Counter

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import GROUP_OPTIONS, PRIMARY_SETTINGS, ST_GROUP, ST_PRESET
from .coordinator import GoProCoordinator
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord: GoProCoordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = [ModeSelect(coord, "mode"), PresetSelect(coord, "preset")]
    present = {int(k) for k in (coord.data or {}).get("settings", {})}
    names = Counter(coord.schema_settings[s]["display_name"] for s in present if s in coord.schema_settings)
    for sid in sorted(present):
        meta = coord.schema_settings.get(sid)
        if not meta or not meta.get("options"):
            continue
        name = meta["display_name"]
        if names[name] > 1:
            cat = coord.setting_category.get(sid)
            name = f"{name} ({cat})" if cat else f"{name} #{sid}"
        entities.append(SettingSelect(coord, sid, name))
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
        super().__init__(coordinator, f"setting_{sid}")
        self.sid = sid
        self._attr_name = name
        self._attr_entity_registry_enabled_default = sid in PRIMARY_SETTINGS
        self._attr_icon = "mdi:tune-variant"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.setting(self.sid) is not None

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
                "category": self.coordinator.setting_category.get(self.sid)}

    async def async_select_option(self, option: str) -> None:
        oid = next((o for o, lbl in self.coordinator.allowed_options(self.sid) if lbl == option), None)
        if oid is None:
            raise HomeAssistantError(f"Option {option} is not allowed in the current configuration")
        await self._call(self.api.set_setting(self.sid, oid))
