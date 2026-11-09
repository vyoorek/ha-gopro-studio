"""Przeglądarka mediów HA: filmy i zdjęcia z karty kamery, z miniaturami i odtwarzaniem."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (BrowseMediaSource, MediaSource, MediaSourceItem, PlayMedia,
                                                   Unresolvable)
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_SECRET_KEY = f"{DOMAIN}_thumb_secret"


def thumb_token(hass: HomeAssistant, entry_id: str, path: str) -> str:
    secret = hass.data.setdefault(_SECRET_KEY, secrets.token_hex(16))
    return hmac.new(secret.encode(), f"{entry_id}/{path}".encode(), hashlib.sha256).hexdigest()[:24]


def thumb_url(hass: HomeAssistant, entry_id: str, path: str, kind: str = "thumb") -> str:
    return f"/api/gopro_studio_thumb/{entry_id}/{kind}/{path}?t={thumb_token(hass, entry_id, path)}"


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    return GoProMediaSource(hass)


class GoProMediaSource(MediaSource):
    name = "GoPro"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _entries(self):
        return [e for e in self.hass.config_entries.async_entries(DOMAIN) if hasattr(e, "runtime_data")]

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        entry_id, _, path = (item.identifier or "").partition("/")
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or not hasattr(entry, "runtime_data") or "/" not in path:
            raise Unresolvable("Unknown GoPro media")
        media = entry.runtime_data.coordinator.find_media(path)
        if media is not None and media.kind == "group":
            path = f"{media.folder}/{media.members[0]}"
        mime = media.mime if media else ("video/mp4" if path.upper().endswith(".MP4") else "image/jpeg")
        # ścieżka względna - HA sam ją podpisze (authSig) przy odtwarzaniu
        return PlayMedia(f"/api/gopro_studio/{entry_id}/media/{path}", mime)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        entries = self._entries()
        ident = item.identifier or ""
        if not ident and len(entries) != 1:
            return BrowseMediaSource(
                domain=DOMAIN, identifier="", media_class=MediaClass.DIRECTORY, media_content_type="",
                title="GoPro", can_play=False, can_expand=True, children_media_class=MediaClass.DIRECTORY,
                children=[BrowseMediaSource(domain=DOMAIN, identifier=e.entry_id, media_class=MediaClass.DIRECTORY,
                                            media_content_type="", title=e.title, can_play=False, can_expand=True)
                          for e in entries])
        entry_id = ident.split("/")[0] if ident else entries[0].entry_id
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or not hasattr(entry, "runtime_data"):
            raise Unresolvable("Unknown GoPro camera")
        coord = entry.runtime_data.coordinator
        if time.time() - coord.media_ts > 15:
            await coord.async_refresh_media()
        children = []
        for m in coord.media:
            video = m.kind == "video"
            title = f"{m.created:%Y-%m-%d %H:%M}  {m.name}"
            if m.raw:
                title += "  [RAW]"
            if m.kind == "group":
                title += f"  ({len(m.members)} zdjęć)"
            children.append(BrowseMediaSource(
                domain=DOMAIN, identifier=f"{entry_id}/{m.path}",
                media_class=MediaClass.VIDEO if video else MediaClass.IMAGE,
                media_content_type=MediaType.VIDEO if video else MediaType.IMAGE,
                title=title, can_play=True, can_expand=False,
                thumbnail=thumb_url(self.hass, entry_id, m.path)))
        return BrowseMediaSource(
            domain=DOMAIN, identifier=entry_id, media_class=MediaClass.DIRECTORY, media_content_type="",
            title=entry.title, can_play=False, can_expand=True, children=children,
            children_media_class=MediaClass.VIDEO)
