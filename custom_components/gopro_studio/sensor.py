"""Sensory GoPro Studio."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity, SensorEntityDescription,
                                             SensorStateClass)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (GROUP_OPTIONS, SD_STATUS, ST_BATT_PCT, ST_BUSY, ST_ENCODING, ST_GROUP, ST_NUM_PHOTOS,
                    ST_NUM_VIDEOS, ST_PHOTOS_LEFT, ST_SD, ST_SD_CAPACITY_KB, ST_SPACE_KB, ST_VIDEO_LEFT,
                    ST_VIDEO_SECS, ST_WIFI_BARS)
from .coordinator import GoProCoordinator
from .entity import GoProEntity


@dataclass(frozen=True, kw_only=True)
class GoProSensorDescription(SensorEntityDescription):
    value_fn: Callable[[GoProCoordinator], Any]


def _state(c: GoProCoordinator) -> str:
    if c.status(ST_ENCODING):
        return "recording"
    return "busy" if c.status(ST_BUSY) else "ready"


SENSORS: tuple[GoProSensorDescription, ...] = (
    GoProSensorDescription(key="battery", translation_key="battery", device_class=SensorDeviceClass.BATTERY,
                           native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
                           value_fn=lambda c: c.status(ST_BATT_PCT)),
    GoProSensorDescription(key="sd_free", translation_key="sd_free", device_class=SensorDeviceClass.DATA_SIZE,
                           native_unit_of_measurement=UnitOfInformation.KILOBYTES,
                           suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
                           suggested_display_precision=1, state_class=SensorStateClass.MEASUREMENT,
                           value_fn=lambda c: c.status(ST_SPACE_KB)),
    GoProSensorDescription(key="sd_capacity", translation_key="sd_capacity", device_class=SensorDeviceClass.DATA_SIZE,
                           native_unit_of_measurement=UnitOfInformation.KILOBYTES,
                           suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
                           suggested_display_precision=1, entity_category=EntityCategory.DIAGNOSTIC,
                           value_fn=lambda c: c.status(ST_SD_CAPACITY_KB) or None),
    GoProSensorDescription(key="video_remaining", translation_key="video_remaining",
                           device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
                           suggested_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=0,
                           value_fn=lambda c: c.status(ST_VIDEO_LEFT)),
    GoProSensorDescription(key="photos_remaining", translation_key="photos_remaining",
                           state_class=SensorStateClass.MEASUREMENT, value_fn=lambda c: c.status(ST_PHOTOS_LEFT)),
    GoProSensorDescription(key="video_count", translation_key="video_count", state_class=SensorStateClass.MEASUREMENT,
                           value_fn=lambda c: c.status(ST_NUM_VIDEOS)),
    GoProSensorDescription(key="photo_count", translation_key="photo_count", state_class=SensorStateClass.MEASUREMENT,
                           value_fn=lambda c: c.status(ST_NUM_PHOTOS)),
    GoProSensorDescription(key="recording_time", translation_key="recording_time",
                           device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
                           value_fn=lambda c: c.status(ST_VIDEO_SECS)),
    GoProSensorDescription(key="camera_state", translation_key="camera_state", device_class=SensorDeviceClass.ENUM,
                           options=["ready", "busy", "recording"], value_fn=_state),
    GoProSensorDescription(key="active_mode", translation_key="active_mode", device_class=SensorDeviceClass.ENUM,
                           options=list(GROUP_OPTIONS.values()),
                           value_fn=lambda c: GROUP_OPTIONS.get(c.status(ST_GROUP))),
    GoProSensorDescription(key="sd_status", translation_key="sd_status", device_class=SensorDeviceClass.ENUM,
                           options=list(dict.fromkeys(SD_STATUS.values())), entity_category=EntityCategory.DIAGNOSTIC,
                           value_fn=lambda c: SD_STATUS.get(c.status(ST_SD, -1), "unknown")),
    GoProSensorDescription(key="wifi_signal", translation_key="wifi_signal", entity_category=EntityCategory.DIAGNOSTIC,
                           state_class=SensorStateClass.MEASUREMENT, value_fn=lambda c: c.status(ST_WIFI_BARS)),
    GoProSensorDescription(key="last_captured", translation_key="last_captured",
                           value_fn=lambda c: c.last_captured),
    GoProSensorDescription(key="media_on_card", translation_key="media_on_card",
                           state_class=SensorStateClass.MEASUREMENT, value_fn=lambda c: len(c.media)),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities(GoProSensor(coord, d) for d in SENSORS)


class GoProSensor(GoProEntity, SensorEntity):
    entity_description: GoProSensorDescription

    def __init__(self, coordinator: GoProCoordinator, description: GoProSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "media_on_card":
            return {"latest": [m.path for m in self.coordinator.media[:10]]}
        return None
