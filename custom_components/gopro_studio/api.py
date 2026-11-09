"""Asynchroniczny klient Open GoPro HTTP API (COHN / Wi-Fi / USB) dla Home Assistanta."""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
from urllib.parse import quote

import aiohttp
from yarl import URL

from .media import MediaItem, parse_media_list

_LOGGER = logging.getLogger(__name__)


class GoProError(Exception):
    """Błąd komunikacji z kamerą."""


class GoProAuthError(GoProError):
    """Błędny login/hasło."""


class GoProApi:
    def __init__(self, session: aiohttp.ClientSession, host: str, username: str, password: str,
                 https: bool = True) -> None:
        self._session = session
        self.host = host.strip()
        self.username = username
        self.password = password
        self.https = https
        if https:
            self.base = f"https://{self.host}"
            self._auth = aiohttp.BasicAuth(username, password)
        else:
            self.base = f"http://{self.host}" if ":" in self.host else f"http://{self.host}:8080"
            self._auth = None

    # ------------------------------------------------------------------ niskopoziomowe
    def url(self, path: str, params: dict | None = None) -> URL:
        """URL z dosłownym "/" w parametrach - kamera nie dekoduje %2F."""
        q = ""
        if params:
            q = "?" + "&".join(f"{k}={quote(str(v), safe='/:,')}" for k, v in params.items())
        return URL(self.base + path + q, encoded=True)

    async def request(self, path: str, params: dict | None = None, timeout: float = 10,
                      raw: bool = False):
        try:
            async with self._session.get(self.url(path, params), auth=self._auth, ssl=False,
                                         timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                body = await resp.read()
                if resp.status == 401:
                    raise GoProAuthError("Invalid username or password")
                if resp.status >= 400:
                    msg = body.decode("utf-8", "replace")[:300]
                    try:
                        j = json.loads(msg)
                        msg = j.get("error") or j.get("message") or msg
                    except (ValueError, AttributeError):
                        pass
                    raise GoProError(f"HTTP {resp.status} {path}: {msg}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GoProError(f"Connection error: {err.__class__.__name__}") from err
        if raw:
            return body
        if not body.strip():
            return {}
        try:
            return json.loads(body)
        except ValueError:
            return {"raw": body.decode("utf-8", "replace")}

    async def open_stream(self, path: str, headers: dict | None = None) -> aiohttp.ClientResponse:
        """Otwiera odpowiedź strumieniowo (proxy plików do przeglądarki mediów)."""
        try:
            return await self._session.get(URL(self.base + path, encoded=True), auth=self._auth, ssl=False,
                                           headers=headers or {}, timeout=aiohttp.ClientTimeout(
                                               total=None, sock_connect=10, sock_read=60))
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GoProError(f"Connection error: {err.__class__.__name__}") from err

    # ------------------------------------------------------------------ informacje
    async def info(self) -> dict:
        return await self.request("/gopro/camera/info")

    async def state(self) -> dict:
        return await self.request("/gopro/camera/state", timeout=6)

    async def schema(self) -> dict:
        return await self.request("/gp/gpControl", timeout=20)

    async def presets(self) -> dict:
        return await self.request("/gopro/camera/presets/get")

    async def media_list(self) -> list[MediaItem]:
        return parse_media_list(await self.request("/gopro/media/list", timeout=30))

    async def media_info(self, path: str) -> dict:
        return await self.request("/gopro/media/info", {"path": path})

    async def thumbnail(self, path: str) -> bytes:
        return await self.request("/gopro/media/thumbnail", {"path": path}, raw=True)

    async def screennail(self, path: str) -> bytes:
        try:
            return await self.request("/gopro/media/screennail", {"path": path}, raw=True, timeout=15)
        except GoProError:
            return await self.thumbnail(path)        # dla filmów kamera zwraca 400

    async def last_captured(self) -> dict:
        return await self.request("/gopro/media/last_captured")

    # ------------------------------------------------------------------ sterowanie
    async def shutter(self, on: bool):
        return await self.request(f"/gopro/camera/shutter/{'start' if on else 'stop'}")

    async def set_group(self, group_id: int):
        return await self.request("/gopro/camera/presets/set_group", {"id": group_id})

    async def load_preset(self, preset_id: int):
        return await self.request("/gopro/camera/presets/load", {"id": preset_id})

    async def set_setting(self, setting_id: int, option: int):
        return await self.request("/gopro/camera/setting", {"setting": setting_id, "option": option})

    async def zoom(self, percent: int):
        return await self.request("/gopro/camera/digital_zoom", {"percent": int(percent)})

    async def hilight(self):
        return await self.request("/gopro/media/hilight/moment")

    async def keep_alive(self):
        return await self.request("/gopro/camera/keep_alive", timeout=4)

    async def turbo(self, on: bool):
        return await self.request("/gopro/media/turbo_transfer", {"p": int(on)})

    async def external_control(self, on: bool):
        return await self.request("/gopro/camera/control/set_ui_controller", {"p": 2 if on else 0})

    async def stream_start(self, port: int = 8554):
        try:
            await self.request("/gopro/camera/stream/stop")
        except GoProError:
            pass
        return await self.request("/gopro/camera/stream/start", {"port": port})

    async def stream_stop(self):
        return await self.request("/gopro/camera/stream/stop")

    async def sync_time(self):
        now = dt.datetime.now().astimezone()
        off = now.utcoffset() or dt.timedelta()
        dst = int(bool(time.localtime().tm_isdst))
        return await self.request("/gopro/camera/set_date_time", {
            "date": f"{now.year}_{now.month}_{now.day}",
            "time": f"{now.hour}_{now.minute}_{now.second}",
            "tzone": int(off.total_seconds() // 60) - 60 * dst, "dst": dst})

    async def locate(self, on: bool):
        return await self.request("/gp/gpControl/command/system/locate", {"p": int(on)})

    async def sleep(self):
        return await self.request("/gp/gpControl/command/system/sleep")

    async def labs(self, code: str) -> str:
        """Komenda GoPro Labs przez Wi-Fi (firmware Labs HERO13 od 2.04.70)."""
        res = await self.request("/gopro/qrcode", {"labs": 1, "code": code}, raw=True)
        return res.decode("utf-8", "replace").strip()

    async def raw_get(self, path: str) -> tuple[int, str]:
        try:
            async with self._session.get(URL(self.base + path, encoded=True), auth=self._auth, ssl=False,
                                         timeout=aiohttp.ClientTimeout(total=15)) as resp:
                body = await resp.read()
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype or "text" in ctype or len(body) < 8192:
                    return resp.status, body.decode("utf-8", "replace")
                return resp.status, f"<{len(body)} bytes, {ctype}>"
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GoProError(f"Connection error: {err.__class__.__name__}") from err

    # ------------------------------------------------------------------ usuwanie
    async def delete(self, item: MediaItem):
        if item.kind == "group":
            return await self.request("/gp/gpControl/command/storage/delete/group", {"p": item.path})
        return await self.request("/gopro/media/delete/file", {"path": item.path})

    async def delete_path(self, path: str):
        return await self.request("/gopro/media/delete/file", {"path": path})

    async def delete_all(self):
        return await self.request("/gp/gpControl/command/storage/delete/all", timeout=60)

    # ------------------------------------------------------------------ pobieranie
    async def download(self, folder: str, name: str, dest: str, executor) -> int:
        """Pobiera plik z wznawianiem (.part). Zapis na dysk odbywa się w wątku (executor)."""
        part = dest + ".part"
        await executor(lambda: os.makedirs(os.path.dirname(dest), exist_ok=True))
        have = await executor(lambda: os.path.getsize(part) if os.path.exists(part) else 0)
        headers = {"Range": f"bytes={have}-"} if have else {}
        resp = await self.open_stream(f"/videos/DCIM/{folder}/{name}", headers)
        try:
            if resp.status == 404:
                raise GoProError(f"File not found: {folder}/{name}")
            if resp.status == 416:
                await executor(os.replace, part, dest)
                return have
            if resp.status >= 400:
                raise GoProError(f"HTTP {resp.status}")
            if resp.status == 200:
                have = 0
            total = have + int(resp.headers.get("Content-Length", 0) or 0)
            fh = await executor(open, part, "ab" if have else "wb")
            done = have
            try:
                async for chunk in resp.content.iter_chunked(1 << 20):
                    await executor(fh.write, chunk)
                    done += len(chunk)
            finally:
                await executor(fh.close)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GoProError(f"Download interrupted: {err.__class__.__name__}") from err
        finally:
            resp.release()
        if total and done < total:
            raise GoProError(f"Incomplete file ({done}/{total})")
        await executor(os.replace, part, dest)
        return done
