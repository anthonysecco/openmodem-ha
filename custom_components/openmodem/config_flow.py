"""Config flow for OpenModem."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SCAN_INTERVAL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN, ENDPOINT_PATH, SECTION_MODEM

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=2, max=300)),
    }
)


async def _validate(hass, host: str, port: int) -> None:
    """Raise on anything other than a working ha_state.sh response."""
    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}{ENDPOINT_PATH}"
    async with asyncio.timeout(10):
        resp = await session.get(url)
        resp.raise_for_status()
        data = await resp.json(content_type=None)
    if not isinstance(data, dict) or SECTION_MODEM not in data:
        raise ValueError("unexpected_response")


class OpenModemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenModem."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            try:
                await _validate(self.hass, host, port)
            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except ClientError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "unexpected_response"
            else:
                return self.async_create_entry(
                    title=f"OpenModem ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
