"""Data update coordinator for OpenModem.

Polls a single endpoint — ha_state.sh — which itself is just a merge of
OpenModem's own state.sh + net_state.sh (see that project's
www/cgi-bin/ha_state.sh). It does no AT-command or network work of its
own on every request; it's exactly as fresh as OpenModem's own pollers,
so this coordinator's scan_interval only controls how often *this*
integration re-reads that already-current data, not how often the
modem itself is polled.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ENDPOINT_PATH, SECTION_CONNECTIVITY, SECTION_MODEM

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class OpenModemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches and caches ha_state.sh's merged modem/connectivity JSON."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._url = f"http://{host}:{port}{ENDPOINT_PATH}"

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await session.get(self._url)
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with OpenModem at {self._url}: {err}") from err

        if not isinstance(data, dict) or SECTION_MODEM not in data:
            raise UpdateFailed(f"Unexpected response shape from {self._url}")

        data.setdefault(SECTION_CONNECTIVITY, {})
        return data
