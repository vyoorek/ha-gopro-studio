"""Encja kamery: obraz = miniatura ostatniego nagrania; opcjonalnie podgląd na żywo (strumień UDP z kamery)."""
from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import GoProError
from .const import CONF_PREVIEW, CONF_PREVIEW_PORT, DEFAULT_PREVIEW, DEFAULT_PREVIEW_PORT
from .entity import GoProEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities([GoProCamera(coord, entry.options.get(CONF_PREVIEW, DEFAULT_PREVIEW),
                                    entry.options.get(CONF_PREVIEW_PORT, DEFAULT_PREVIEW_PORT))])


class GoProCamera(GoProEntity, Camera):
    _attr_translation_key = "camera"

    def __init__(self, coordinator, preview: bool, port: int) -> None:
        GoProEntity.__init__(self, coordinator, "camera")
        Camera.__init__(self)
        self._preview = preview
        self._port = port
        self._image: bytes | None = None
        self._image_path: str | None = None
        if preview:
            self._attr_supported_features = CameraEntityFeature.STREAM

    @property
    def is_recording(self) -> bool:
        return bool(self.coordinator.status(10))

    @property
    def extra_state_attributes(self):
        return {"last_captured": self.coordinator.last_captured, "preview_port": self._port if self._preview else None}

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        path = self.coordinator.last_captured
        if path and path != self._image_path:
            try:
                self._image = await self.api.screennail(path)
                self._image_path = path
            except GoProError:
                pass
        return self._image

    async def stream_source(self) -> str | None:
        """Kamera wysyła podgląd (MPEG-TS po UDP) na adres, z którego przyszło zapytanie, czyli na HA."""
        if not self._preview:
            return None
        try:
            await self.api.stream_start(self._port)
        except GoProError:
            return None
        return f"udp://0.0.0.0:{self._port}?overrun_nonfatal=1&fifo_size=5000000"
