"""Koordynator: cykliczny odczyt stanu kamery, presety, lista mediów, keep-alive."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoProApi, GoProAuthError, GoProError
from .const import (CONF_KEEP_ALIVE, CONF_SCAN_INTERVAL, DEFAULT_KEEP_ALIVE, DEFAULT_SCAN_INTERVAL, DOMAIN,
                    GROUP_KEYS, RESOLUTION_LABELS, SKIP_CATEGORIES, ST_BUSY, ST_ENCODING, ST_GROUP)
from .media import MediaItem

_LOGGER = logging.getLogger(__name__)


def _prettify_preset(p: dict) -> str:
    if p.get("customName"):
        return p["customName"]
    t = p.get("titleId", "") or p.get("mode", "")
    for pre in ("PRESET_TITLE_", "FLAT_MODE_"):
        t = t.replace(pre, "")
    return t.replace("_", " ").title()


class GoProCoordinator(DataUpdateCoordinator[dict]):
    """Dane: {"status": {...}, "settings": {...}} z /gopro/camera/state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: GoProApi, info: dict, schema: dict) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} {info.get('serial_number', '')}",
                         update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL,
                                                                              DEFAULT_SCAN_INTERVAL)))
        self.api = api
        self.info = info
        self.serial: str = info.get("serial_number", entry.entry_id)
        self.presets: dict[int, list[tuple[int, str]]] = {}
        self.media: list[MediaItem] = []
        self.media_ts = 0.0
        self.last_captured: str | None = None
        self._presets_ts = 0.0
        self._last_keep = 0.0
        self._prev_group = None
        self._was_encoding = False
        self._was_busy = False
        self.schema_settings: dict[int, dict] = {s["id"]: s for s in schema.get("settings", [])}
        self.schema_filters: list = schema.get("filters", [])
        self.status_names = {f["id"]: f["name"] for g in schema.get("status", {}).get("groups", [])
                             for f in g.get("fields", [])}
        self.setting_category: dict[int, str] = {}
        for h in schema.get("display_hints", []):
            if h.get("display_name") in SKIP_CATEGORIES:
                continue
            for s in h.get("settings", []):
                self.setting_category.setdefault(s.get("setting_id"), h.get("display_name", ""))

    # ------------------------------------------------------------------ aktualizacja
    @property
    def keep_alive_enabled(self) -> bool:
        return self.config_entry.options.get(CONF_KEEP_ALIVE, DEFAULT_KEEP_ALIVE)

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.state()
        except GoProAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GoProError as err:
            raise UpdateFailed(str(err)) from err
        if not isinstance(data, dict) or "status" not in data:
            raise UpdateFailed("Unexpected response from camera")

        now = time.monotonic()
        if self.keep_alive_enabled and now - self._last_keep > 3:
            self._last_keep = now
            try:
                await self.api.keep_alive()
            except GoProError:
                pass

        status = data["status"]
        group = status.get(str(ST_GROUP))
        if not self.presets or group != self._prev_group or now - self._presets_ts > 120:
            await self._refresh_presets()
            self._prev_group = group

        encoding = bool(status.get(str(ST_ENCODING)))
        busy = bool(status.get(str(ST_BUSY)))
        if (self._was_encoding and not encoding) or (self._was_busy and not busy and not encoding) \
                or not self.media_ts:
            self.hass.async_create_task(self.async_refresh_media())
        self._was_encoding, self._was_busy = encoding, busy
        return data

    async def _refresh_presets(self) -> None:
        try:
            data = await self.api.presets()
        except GoProError:
            return
        self._presets_ts = time.monotonic()
        presets: dict[int, list[tuple[int, str]]] = {}
        for g in data.get("presetGroupArray", []):
            gid = GROUP_KEYS.get(g.get("id"))
            if gid is not None:
                presets[gid] = [(p["id"], _prettify_preset(p)) for p in g.get("presetArray", [])]
        self.presets = presets

    async def async_refresh_media(self) -> None:
        try:
            self.media = await self.api.media_list()
            last = await self.api.last_captured()
            self.last_captured = f"{last.get('folder')}/{last.get('file')}" if last.get("file") else (
                self.media[0].path if self.media else None)
        except GoProError as err:
            _LOGGER.debug("Media list failed: %s", err)
            return
        self.media_ts = time.time()
        self.async_update_listeners()

    # ------------------------------------------------------------------ pomocnicze
    def status(self, sid: int, default: Any = 0) -> Any:
        return (self.data or {}).get("status", {}).get(str(sid), default)

    def setting(self, sid: int, default: Any = None) -> Any:
        return (self.data or {}).get("settings", {}).get(str(sid), default)

    def option_label(self, sid: int, oid: Any) -> str:
        if sid == 2 and oid in RESOLUTION_LABELS:
            return RESOLUTION_LABELS[oid]
        meta = self.schema_settings.get(sid)
        if meta:
            for o in meta["options"]:
                if o["id"] == oid:
                    return o["display_name"]
        return f"#{oid}"

    def allowed_options(self, sid: int) -> list[tuple[int, str]]:
        """Opcje dozwolone przy bieżącej konfiguracji (reguły "filters" z gpControl)."""
        meta = self.schema_settings[sid]
        settings = (self.data or {}).get("settings", {})
        status = (self.data or {}).get("status", {})
        blocked: set[int] = set()
        for flt in self.schema_filters:
            active = True
            for cond in flt.get("activated_by", []):
                if "setting_id" in cond and settings.get(str(cond["setting_id"])) not in cond.get("ids", []):
                    active = False
                    break
                if "status_id" in cond and status.get(str(cond["status_id"])) not in cond.get("values", []):
                    active = False
                    break
            if active:
                for bl in flt.get("blacklist", []):
                    if bl.get("setting_id") == sid:
                        blocked.update(bl.get("opt_ids", []))
        cur = settings.get(str(sid))
        opts = [o for o in meta["options"] if o["id"] not in blocked or o["id"] == cur]
        labels = [self.option_label(sid, o["id"]) for o in opts]
        out = []
        for o, lbl in zip(opts, labels):
            if labels.count(lbl) > 1:
                lbl = f"{lbl} (#{o['id']})"
            out.append((o["id"], lbl))
        return out

    def find_media(self, path: str) -> MediaItem | None:
        return next((m for m in self.media if m.path == path), None)
