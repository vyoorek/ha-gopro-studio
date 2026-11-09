"""Czujniki binarne GoPro Studio."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (BinarySensorDeviceClass, BinarySensorEntity,
                                                    BinarySensorEntityDescription)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ST_BATT_BARS, ST_BUSY, ST_COLD, ST_ENCODING, ST_HOT, ST_PREVIEW, ST_SD, ST_USB
from .coordinator import GoProCoordinator
from .entity import GoProEntity


@dataclass(frozen=True, kw_only=True)
class GoProBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[GoProCoordinator], bool]


BINARY: tuple[GoProBinaryDescription, ...] = (
    GoProBinaryDescription(key="recording", translation_key="recording", device_class=BinarySensorDeviceClass.RUNNING,
                           value_fn=lambda c: bool(c.status(ST_ENCODING))),
    GoProBinaryDescription(key="busy", translation_key="busy", value_fn=lambda c: bool(c.status(ST_BUSY))),
    GoProBinaryDescription(key="overheating", translation_key="overheating", device_class=BinarySensorDeviceClass.HEAT,
                           value_fn=lambda c: bool(c.status(ST_HOT))),
    GoProBinaryDescription(key="too_cold", translation_key="too_cold", device_class=BinarySensorDeviceClass.COLD,
                           value_fn=lambda c: bool(c.status(ST_COLD))),
    GoProBinaryDescription(key="charging", translation_key="charging",
                           device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
                           value_fn=lambda c: c.status(ST_BATT_BARS) == 4),
    GoProBinaryDescription(key="sd_problem", translation_key="sd_problem", device_class=BinarySensorDeviceClass.PROBLEM,
                           entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda c: c.status(ST_SD, 0) not in (0,)),
    GoProBinaryDescription(key="usb", translation_key="usb", device_class=BinarySensorDeviceClass.PLUG,
                           entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda c: bool(c.status(ST_USB))),
    GoProBinaryDescription(key="preview_active", translation_key="preview_active",
                           entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda c: bool(c.status(ST_PREVIEW))),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities(GoProBinarySensor(coord, d) for d in BINARY)


class GoProBinarySensor(GoProEntity, BinarySensorEntity):
    entity_description: GoProBinaryDescription

    def __init__(self, coordinator: GoProCoordinator, description: GoProBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator)
