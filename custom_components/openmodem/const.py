"""Constants for the OpenModem integration."""

DOMAIN = "openmodem"

CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 10  # seconds — matches OpenModem's own default POLL_INTERVAL

ENDPOINT_PATH = "/cgi-bin/ha_state.sh"

SECTION_MODEM = "modem"
SECTION_CONNECTIVITY = "connectivity"
