"""GoPro Studio - sterowanie kamerą GoPro (Open GoPro HTTP / COHN) i funkcjami GoPro Labs z Home Assistanta."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import voluptuous as vol
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GoProApi, GoProAuthError, GoProError
from .const import (CONF_DOWNLOAD_DIR, CONF_HTTPS, DOMAIN, EVENT_DOWNLOAD_FINISHED, EVENT_LABS_SENT)
from .coordinator import GoProCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.BUTTON, Platform.SELECT,
             Platform.NUMBER, Platform.TEXT, Platform.CAMERA]


@dataclass
class GoProData:
    api: GoProApi
    coordinator: GoProCoordinator


GoProConfigEntry = ConfigEntry[GoProData]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.http.register_view(GoProMediaView(hass))
    hass.http.register_view(GoProThumbView(hass))
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GoProConfigEntry) -> bool:
    session = async_get_clientsession(hass, verify_ssl=False)
    api = GoProApi(session, entry.data[CONF_HOST], entry.data.get(CONF_USERNAME, ""),
                   entry.data.get(CONF_PASSWORD, ""), entry.data.get(CONF_HTTPS, True))
    try:
        info = await api.info()
        schema = await api.schema()
    except GoProAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except GoProError as err:
        raise ConfigEntryNotReady(f"Camera not reachable at {entry.data[CONF_HOST]}: {err}") from err

    coordinator = GoProCoordinator(hass, entry, api, info, schema)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = GoProData(api, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: GoProConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: GoProConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ====================================================================== proxy plików z kamery
class GoProMediaView(HomeAssistantView):
    """Udostępnia pliki/miniatury z kamery przeglądarce (kamera wymaga Basic Auth + własnego certyfikatu)."""

    url = "/api/gopro_studio/{entry_id}/{kind}/{folder}/{name}"
    name = "api:gopro_studio:media"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, kind: str, folder: str, name: str):
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        api: GoProApi = entry.runtime_data.api
        path = f"{folder}/{name}"
        try:
            if kind == "thumb":
                return web.Response(body=await api.thumbnail(path), content_type="image/jpeg",
                                    headers={"Cache-Control": "max-age=86400"})
            if kind == "screennail":
                return web.Response(body=await api.screennail(path), content_type="image/jpeg",
                                    headers={"Cache-Control": "max-age=86400"})
        except GoProError:
            return web.Response(status=502)
        if kind != "media":
            return web.Response(status=404)
        headers = {}
        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]
        try:
            upstream = await api.open_stream(f"/videos/DCIM/{folder}/{name}", headers)
        except GoProError:
            return web.Response(status=502)
        try:
            resp = web.StreamResponse(status=upstream.status)
            for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "Last-Modified"):
                if h in upstream.headers:
                    resp.headers[h] = upstream.headers[h]
            resp.headers.setdefault("Accept-Ranges", "bytes")
            await resp.prepare(request)
            async for chunk in upstream.content.iter_chunked(256 * 1024):
                await resp.write(chunk)
            await resp.write_eof()
            return resp
        except (ConnectionResetError, OSError):
            return web.Response(status=499)
        finally:
            upstream.release()


class GoProThumbView(HomeAssistantView):
    """Miniatury dla przeglądarki mediów (<img> nie wysyła tokenu HA - chronione podpisem HMAC)."""

    url = "/api/gopro_studio_thumb/{entry_id}/{kind}/{folder}/{name}"
    name = "api:gopro_studio:thumb"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, kind: str, folder: str, name: str):
        from .media_source import thumb_token
        path = f"{folder}/{name}"
        if kind not in ("thumb", "screennail") or request.query.get("t") != thumb_token(self.hass, entry_id, path):
            return web.Response(status=403)
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        api: GoProApi = entry.runtime_data.api
        try:
            data = await (api.thumbnail(path) if kind == "thumb" else api.screennail(path))
        except GoProError:
            return web.Response(status=502)
        return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})


# ====================================================================== usługi
def _entry_for(hass: HomeAssistant, call: ServiceCall) -> GoProConfigEntry:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if hasattr(e, "runtime_data")]
    wanted = call.data.get("config_entry_id")
    if wanted:
        entries = [e for e in entries if e.entry_id == wanted]
    if not entries:
        raise HomeAssistantError("No loaded GoPro Studio camera (check config_entry_id)")
    return entries[0]


def download_dir(hass: HomeAssistant, entry: GoProConfigEntry, override: str | None = None) -> str:
    if override:
        return override
    if entry.options.get(CONF_DOWNLOAD_DIR):
        return entry.options[CONF_DOWNLOAD_DIR]
    base = hass.config.media_dirs.get("local") or hass.config.path("media")
    return os.path.join(base, "gopro")


async def async_download_items(hass: HomeAssistant, entry: GoProConfigEntry, items, include_raw=True,
                               include_lrv=False, directory: str | None = None, by_date=True,
                               skip_existing=True, delete_after=False) -> list[str]:
    api = entry.runtime_data.api
    coord = entry.runtime_data.coordinator
    root = download_dir(hass, entry, directory)
    saved: list[str] = []
    try:
        await api.turbo(True)
    except GoProError:
        pass
    try:
        for item in items:
            base = os.path.join(root, item.created.strftime("%Y-%m-%d")) if by_date else root
            ok_all = True
            for name in item.files(include_raw, include_lrv):
                dest = os.path.join(base, name)
                if skip_existing and await hass.async_add_executor_job(os.path.exists, dest):
                    continue
                try:
                    await api.download(item.folder, name, dest, hass.async_add_executor_job)
                    ts = item.created.timestamp()
                    await hass.async_add_executor_job(os.utime, dest, (ts, ts))
                    saved.append(dest)
                    hass.bus.async_fire(EVENT_DOWNLOAD_FINISHED, {"camera": coord.serial, "file": f"{item.folder}/{name}",
                                                                  "path": dest})
                except GoProError as err:
                    ok_all = False
                    _LOGGER.warning("Download of %s/%s failed: %s", item.folder, name, err)
            if delete_after and ok_all:
                try:
                    await api.delete(item)
                except GoProError as err:
                    _LOGGER.warning("Delete after download failed for %s: %s", item.path, err)
    finally:
        try:
            await api.turbo(False)
        except GoProError:
            pass
    if delete_after:
        await coord.async_refresh_media()
    return saved


def _register_services(hass: HomeAssistant) -> None:
    base = {vol.Optional("config_entry_id"): cv.string}

    async def labs_command(call: ServiceCall) -> ServiceResponse:
        entry = _entry_for(hass, call)
        try:
            res = await entry.runtime_data.api.labs(call.data["command"])
        except GoProError as err:
            raise HomeAssistantError(str(err)) from err
        hass.bus.async_fire(EVENT_LABS_SENT, {"camera": entry.runtime_data.coordinator.serial,
                                              "command": call.data["command"]})
        return {"response": res}

    async def set_setting(call: ServiceCall) -> None:
        entry = _entry_for(hass, call)
        try:
            await entry.runtime_data.api.set_setting(call.data["setting_id"], call.data["option_id"])
        except GoProError as err:
            raise HomeAssistantError(str(err)) from err
        await entry.runtime_data.coordinator.async_request_refresh()

    async def load_preset(call: ServiceCall) -> None:
        entry = _entry_for(hass, call)
        try:
            await entry.runtime_data.api.load_preset(call.data["preset_id"])
        except GoProError as err:
            raise HomeAssistantError(str(err)) from err
        await entry.runtime_data.coordinator.async_request_refresh()

    async def download_media(call: ServiceCall) -> ServiceResponse:
        entry = _entry_for(hass, call)
        coord = entry.runtime_data.coordinator
        await coord.async_refresh_media()
        what = call.data.get("files", "latest")
        path = call.data.get("path")
        if path:
            items = [m for m in coord.media if m.path == path or m.name == path]
        elif what == "all":
            items = list(coord.media)
        elif what == "new":
            items = list(coord.media)       # skip_existing pomija już pobrane
        else:
            items = [coord.find_media(coord.last_captured)] if coord.last_captured else coord.media[:1]
            items = [i for i in items if i]
        if not items:
            raise HomeAssistantError("Nothing to download")
        saved = await async_download_items(
            hass, entry, items, include_raw=call.data.get("include_raw", True),
            include_lrv=call.data.get("include_lrv", False), directory=call.data.get("directory"),
            by_date=call.data.get("by_date", True), skip_existing=call.data.get("skip_existing", True),
            delete_after=call.data.get("delete_after", False))
        return {"saved": saved, "count": len(saved)}

    async def delete_media(call: ServiceCall) -> None:
        entry = _entry_for(hass, call)
        coord = entry.runtime_data.coordinator
        api = entry.runtime_data.api
        try:
            if call.data.get("all"):
                await api.delete_all()
            else:
                path = call.data.get("path")
                if not path:
                    raise HomeAssistantError("Provide 'path' or 'all: true'")
                item = coord.find_media(path)
                await (api.delete(item) if item else api.delete_path(path))
        except GoProError as err:
            raise HomeAssistantError(str(err)) from err
        await coord.async_refresh_media()

    async def http_get(call: ServiceCall) -> ServiceResponse:
        entry = _entry_for(hass, call)
        path = call.data["path"]
        if not path.startswith("/"):
            path = "/" + path
        try:
            code, body = await entry.runtime_data.api.raw_get(path)
        except GoProError as err:
            raise HomeAssistantError(str(err)) from err
        return {"status": code, "body": body}

    hass.services.async_register(DOMAIN, "labs_command", labs_command,
                                 vol.Schema({**base, vol.Required("command"): cv.string}),
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "set_setting", set_setting, vol.Schema({
        **base, vol.Required("setting_id"): vol.Coerce(int), vol.Required("option_id"): vol.Coerce(int)}))
    hass.services.async_register(DOMAIN, "load_preset", load_preset, vol.Schema({
        **base, vol.Required("preset_id"): vol.Coerce(int)}))
    hass.services.async_register(DOMAIN, "download_media", download_media, vol.Schema({
        **base, vol.Optional("files", default="latest"): vol.In(["latest", "new", "all"]),
        vol.Optional("path"): cv.string, vol.Optional("include_raw", default=True): cv.boolean,
        vol.Optional("include_lrv", default=False): cv.boolean, vol.Optional("directory"): cv.string,
        vol.Optional("by_date", default=True): cv.boolean, vol.Optional("skip_existing", default=True): cv.boolean,
        vol.Optional("delete_after", default=False): cv.boolean}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "delete_media", delete_media, vol.Schema({
        **base, vol.Optional("path"): cv.string, vol.Optional("all", default=False): cv.boolean}))
    hass.services.async_register(DOMAIN, "http_get", http_get, vol.Schema({**base, vol.Required("path"): cv.string}),
                                 supports_response=SupportsResponse.ONLY)
