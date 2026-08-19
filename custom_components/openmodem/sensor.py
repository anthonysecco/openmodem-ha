"""Sensor platform for OpenModem.

Field -> entity mapping follows the classification worked out against
OpenModem's own state.sh/net_state.sh (see that project's data
inventory). A few fields are deliberately left out — see this repo's
README "What's not included" section for the full list and why.

reg_lte/reg_nr/reg_creg/carrier_act arrive from ha_state.sh already
translated from raw AT status codes to strings (e.g. "home", "eutran")
rather than numbers — done there because ha_state.sh's fallback for an
unrecognized code is "code_N", which is open-ended and doesn't fit
Home Assistant's enum device class (which requires a fixed, closed set
of options declared up front). They're exposed here as plain string
sensors rather than device_class=enum for that reason.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfDataRate,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SECTION_CONNECTIVITY, SECTION_MODEM
from .coordinator import OpenModemCoordinator
from .entity import OpenModemEntity


@dataclass(frozen=True, kw_only=True)
class OpenModemSensorEntityDescription(SensorEntityDescription):
    """Adds which top-level JSON section a field lives under, plus an
    optional value transform (used for the two epoch timestamps)."""

    section: str
    value_fn: Callable[[Any], Any] | None = None


def _epoch_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return dt_util.utc_from_timestamp(float(value))


SENSOR_DESCRIPTIONS: tuple[OpenModemSensorEntityDescription, ...] = (
    # -- Device --------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="device_model", section=SECTION_MODEM, name="Model",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="device_imei", section=SECTION_MODEM, name="IMEI",
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
    ),
    OpenModemSensorEntityDescription(
        key="device_firmware", section=SECTION_MODEM, name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="device_temp_c", section=SECTION_MODEM, name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="device_uptime_s", section=SECTION_MODEM, name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- SIM -------------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="sim_status", section=SECTION_MODEM, name="SIM Status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="sim_imsi", section=SECTION_MODEM, name="SIM IMSI",
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
    ),
    OpenModemSensorEntityDescription(
        key="sim_iccid", section=SECTION_MODEM, name="SIM ICCID",
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
    ),
    OpenModemSensorEntityDescription(
        key="sim_active_slot", section=SECTION_MODEM, name="SIM Active Slot",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="sim_phone", section=SECTION_MODEM, name="SIM Phone Number",
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
    ),
    # -- Registration ------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="reg_lte", section=SECTION_MODEM, name="LTE Registration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="reg_nr", section=SECTION_MODEM, name="5G NR Registration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="reg_creg", section=SECTION_MODEM, name="Circuit-Switched Registration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Signal --------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="signal_lte_rsrp", section=SECTION_MODEM, name="LTE RSRP",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="signal_lte_rsrq", section=SECTION_MODEM, name="LTE RSRQ",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="signal_lte_sinr", section=SECTION_MODEM, name="LTE SINR",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="signal_nr_rsrp", section=SECTION_MODEM, name="5G NR RSRP",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="signal_nr_rsrq", section=SECTION_MODEM, name="5G NR RSRQ",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="signal_nr_sinr", section=SECTION_MODEM, name="5G NR SINR",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # -- Serving Cell: LTE -----------------------------------------------
    OpenModemSensorEntityDescription(
        key="cell_lte_state", section=SECTION_MODEM, name="LTE Cell State",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_mcc", section=SECTION_MODEM, name="LTE MCC",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_mnc", section=SECTION_MODEM, name="LTE MNC",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_id", section=SECTION_MODEM, name="LTE Cell ID",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_pcid", section=SECTION_MODEM, name="LTE Physical Cell ID",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_earfcn", section=SECTION_MODEM, name="LTE EARFCN",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_band", section=SECTION_MODEM, name="LTE Band",
    ),
    OpenModemSensorEntityDescription(
        key="cell_lte_tac", section=SECTION_MODEM, name="LTE Tracking Area Code",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Serving Cell: NR --------------------------------------------------
    OpenModemSensorEntityDescription(
        key="cell_nr_type", section=SECTION_MODEM, name="5G NR Type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_state", section=SECTION_MODEM, name="5G NR Cell State",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_mcc", section=SECTION_MODEM, name="5G NR MCC",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_mnc", section=SECTION_MODEM, name="5G NR MNC",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_id", section=SECTION_MODEM, name="5G NR Cell ID",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_pcid", section=SECTION_MODEM, name="5G NR Physical Cell ID",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_arfcn", section=SECTION_MODEM, name="5G NR ARFCN",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_band", section=SECTION_MODEM, name="5G NR Band",
    ),
    OpenModemSensorEntityDescription(
        key="cell_nr_tac", section=SECTION_MODEM, name="5G NR Tracking Area Code",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Carrier -------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="carrier_name", section=SECTION_MODEM, name="Carrier",
    ),
    OpenModemSensorEntityDescription(
        key="carrier_act", section=SECTION_MODEM, name="Access Technology",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="carrier_plmn", section=SECTION_MODEM, name="Carrier PLMN",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Network / band preferences (read-only — see README) -------------
    OpenModemSensorEntityDescription(
        key="net_mode_pref", section=SECTION_MODEM, name="Preferred Network Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="band_pref_lte", section=SECTION_MODEM, name="LTE Band Preference",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="band_pref_nr5g", section=SECTION_MODEM, name="5G NR Band Preference",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Carrier Aggregation ---------------------------------------------
    OpenModemSensorEntityDescription(
        key="ca_count", section=SECTION_MODEM, name="Carrier Aggregation Count",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="ca_total_bw_mhz", section=SECTION_MODEM, name="Aggregate Bandwidth",
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="ca_dl_estimated_mbps", section=SECTION_MODEM, name="Estimated Downlink Throughput",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="ca_dl_maximum_mbps", section=SECTION_MODEM, name="Maximum Downlink Throughput",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # -- WAN -------------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="wan_apn", section=SECTION_MODEM, name="APN",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="wan_ip", section=SECTION_MODEM, name="WAN IPv4 Address",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="wan_ipv6", section=SECTION_MODEM, name="WAN IPv6 Address",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="wan_ip_type", section=SECTION_MODEM, name="WAN IP Type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="wan_data_tx", section=SECTION_MODEM, name="WAN Data Sent",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    OpenModemSensorEntityDescription(
        key="wan_data_rx", section=SECTION_MODEM, name="WAN Data Received",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    OpenModemSensorEntityDescription(
        key="wan_rx_rate_bps", section=SECTION_MODEM, name="WAN Receive Rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="wan_tx_rate_bps", section=SECTION_MODEM, name="WAN Send Rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # -- LAN -------------------------------------------------------------
    OpenModemSensorEntityDescription(
        key="lan_router_ip", section=SECTION_MODEM, name="LAN Router IP",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="lan_dhcp_start", section=SECTION_MODEM, name="DHCP Range Start",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="lan_dhcp_end", section=SECTION_MODEM, name="DHCP Range End",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="lan_mode", section=SECTION_MODEM, name="LAN Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="lan_mpdn_mac", section=SECTION_MODEM, name="Passthrough MAC",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="lan_dns_mode", section=SECTION_MODEM, name="DNS Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Poll bookkeeping --------------------------------------------------
    OpenModemSensorEntityDescription(
        key="_polled_at", section=SECTION_MODEM, name="Modem Last Polled",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_epoch_to_datetime,
    ),
    # -- Connectivity (net_state.sh) --------------------------------------
    OpenModemSensorEntityDescription(
        key="icmp_target", section=SECTION_CONNECTIVITY, name="Ping Target",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="icmp_avg_rtt_ms", section=SECTION_CONNECTIVITY, name="Ping Latency",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="icmp_jitter_ms", section=SECTION_CONNECTIVITY, name="Ping Jitter",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OpenModemSensorEntityDescription(
        key="cf_pop", section=SECTION_CONNECTIVITY, name="Cloudflare PoP",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="geo_city", section=SECTION_CONNECTIVITY, name="WAN Egress City",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="geo_region", section=SECTION_CONNECTIVITY, name="WAN Egress Region",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="geo_country", section=SECTION_CONNECTIVITY, name="WAN Egress Country",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OpenModemSensorEntityDescription(
        key="_polled_at", section=SECTION_CONNECTIVITY, name="Connectivity Last Polled",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_epoch_to_datetime,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up OpenModem sensors from a config entry."""
    coordinator: OpenModemCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OpenModemSensor(coordinator, entry.entry_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class OpenModemSensor(OpenModemEntity, SensorEntity):
    """A single OpenModem field exposed as a sensor."""

    entity_description: OpenModemSensorEntityDescription

    def __init__(
        self,
        coordinator: OpenModemCoordinator,
        entry_id: str,
        description: OpenModemSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        # section+key together are unique across both JSON sections
        # (both carry a "_polled_at" field, hence needing the section
        # prefix here rather than just the bare key).
        self._attr_unique_id = f"{entry_id}_{description.section}_{description.key}"

    @property
    def native_value(self):
        value = self._value(self.entity_description.section, self.entity_description.key)
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)
        return value

    @property
    def extra_state_attributes(self):
        # Carrier Aggregation Count's per-carrier detail (type, band,
        # earfcn, bandwidth, pci, rsrp/rsrq/sinr, mimo layers, per-carrier
        # est./max Mbps) is too nested for its own entity — it rides as
        # attributes on this one instead, keyed by "carriers".
        if self.entity_description.key == "ca_count" and self.entity_description.section == SECTION_MODEM:
            bands = self._value(SECTION_MODEM, "ca_bands")
            if bands:
                return {"carriers": bands}
        return None
