"""Config flow for MyAir3 integration."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


async def validate_host(hass: HomeAssistant, host: str) -> bool:
    """Validate connection to MyAir3 system."""
    session = async_get_clientsession(hass)
    try:
        # First authenticate
        async with session.get(
            f"http://{host}/login?password=password",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return False

        # Then try to fetch system data
        async with session.get(
            f"http://{host}/getSystemData",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return resp.status == 200
    except (TimeoutError, aiohttp.ClientError, OSError) as err:
        _LOGGER.error("Failed to connect: %s", err)
        return False


class MyAir3ConfigFlow(config_entries.ConfigFlow, domain="myair3"):
    """Handle a config flow for MyAir3."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Validate connection
            if not await validate_host(self.hass, host):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"MyAir3 ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example": "192.168.1.100",
            },
        )
