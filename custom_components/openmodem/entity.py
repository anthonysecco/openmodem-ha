"""Base entity for OpenModem — groups every sensor/binary_sensor under one device."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SECTION_MODEM
from .coordinator import OpenModemCoordinator


class OpenModemEntity(CoordinatorEntity[OpenModemCoordinator]):
    """Common device grouping + value lookup for OpenModem entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OpenModemCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        modem = coordinator.data.get(SECTION_MODEM, {}) if coordinator.data else {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="OpenModem",
            manufacturer="Quectel",
            model=modem.get("device_model"),
            sw_version=modem.get("device_firmware"),
        )

    def _value(self, section: str, key: str):
        section_data = self.coordinator.data.get(section) if self.coordinator.data else None
        if not isinstance(section_data, dict):
            return None
        return section_data.get(key)
