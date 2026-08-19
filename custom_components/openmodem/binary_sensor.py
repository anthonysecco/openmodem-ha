"""Binary sensor platform for OpenModem."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SECTION_CONNECTIVITY, SECTION_MODEM
from .coordinator import OpenModemCoordinator
from .entity import OpenModemEntity


@dataclass(frozen=True, kw_only=True)
class OpenModemBinarySensorEntityDescription(BinarySensorEntityDescription):
    section: str
    is_on_fn: Callable[[Any], bool | None] = lambda v: bool(v) if v is not None else None


def _is_online(value: Any) -> bool | None:
    if value is None:
        return None
    return value == "online"


BINARY_SENSOR_DESCRIPTIONS: tuple[OpenModemBinarySensorEntityDescription, ...] = (
    OpenModemBinarySensorEntityDescription(
        key="cell_lte_active", section=SECTION_MODEM, name="LTE Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    OpenModemBinarySensorEntityDescription(
        key="cell_nr_active", section=SECTION_MODEM, name="5G NR Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    OpenModemBinarySensorEntityDescription(
        key="wan_active", section=SECTION_MODEM, name="WAN Active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    OpenModemBinarySensorEntityDescription(
        key="net_data_roaming", section=SECTION_MODEM, name="Data Roaming",
    ),
    OpenModemBinarySensorEntityDescription(
        key="icmp_status", section=SECTION_CONNECTIVITY, name="Ping Reachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=_is_online,
    ),
    OpenModemBinarySensorEntityDescription(
        key="check204_status", section=SECTION_CONNECTIVITY, name="Internet Reachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=_is_online,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up OpenModem binary sensors from a config entry."""
    coordinator: OpenModemCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OpenModemBinarySensor(coordinator, entry.entry_id, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class OpenModemBinarySensor(OpenModemEntity, BinarySensorEntity):
    """A single OpenModem boolean/status field exposed as a binary_sensor."""

    entity_description: OpenModemBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: OpenModemCoordinator,
        entry_id: str,
        description: OpenModemBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.section}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        value = self._value(self.entity_description.section, self.entity_description.key)
        return self.entity_description.is_on_fn(value)
