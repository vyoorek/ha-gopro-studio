"""Przyciski GoPro Studio."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import GoProEntity


async def _locate(api):
    await api.locate(True)
    await asyncio.sleep(5)
    await api.locate(False)


async def _download_latest(btn: "GoProButton"):
    from . import async_download_items
    coord = btn.coordinator
    await coord.async_refresh_media()
    item = coord.find_media(coord.last_captured) if coord.last_captured else None
    if item:
        await async_download_items(btn.hass, coord.config_entry, [item])


@dataclass(frozen=True, kw_only=True)
class GoProButtonDescription(ButtonEntityDescription):
    press_fn: Callable[["GoProButton"], Coroutine[Any, Any, Any]]
    refresh: bool = True


BUTTONS: tuple[GoProButtonDescription, ...] = (
    GoProButtonDescription(key="shutter", translation_key="shutter", press_fn=lambda b: b.api.shutter(True)),
    GoProButtonDescription(key="stop", translation_key="stop", press_fn=lambda b: b.api.shutter(False)),
    GoProButtonDescription(key="hilight", translation_key="hilight", press_fn=lambda b: b.api.hilight()),
    GoProButtonDescription(key="sync_time", translation_key="sync_time", entity_category=EntityCategory.CONFIG,
                           press_fn=lambda b: b.api.sync_time()),
    GoProButtonDescription(key="locate", translation_key="locate", press_fn=lambda b: _locate(b.api)),
    GoProButtonDescription(key="sleep", translation_key="sleep", entity_category=EntityCategory.CONFIG,
                           press_fn=lambda b: b.api.sleep(), refresh=False),
    GoProButtonDescription(key="refresh_media", translation_key="refresh_media",
                           entity_category=EntityCategory.DIAGNOSTIC,
                           press_fn=lambda b: b.coordinator.async_refresh_media(), refresh=False),
    GoProButtonDescription(key="download_latest", translation_key="download_latest",
                           press_fn=_download_latest, refresh=False),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities(GoProButton(coord, d) for d in BUTTONS)


class GoProButton(GoProEntity, ButtonEntity):
    entity_description: GoProButtonDescription

    def __init__(self, coordinator, description: GoProButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self._call(self.entity_description.press_fn(self), refresh=self.entity_description.refresh)
