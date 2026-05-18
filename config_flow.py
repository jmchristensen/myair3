"""Config flow for MyAir3 integration."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_PASSWORD, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

CONFIG_VERSION = 2


async def validate_host(hass: HomeAssistant, host: str, password: str) -> bool:
    """Validate connection to MyAir3 system."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"http://{host}/login?password={password}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return False

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

    VERSION = CONFIG_VERSION

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)
            if not await validate_host(self.hass, host, password):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"MyAir3 ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example": "192.168.1.100",
            },
        )


class MyAir3OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for MyAir3."""

    async def async_step_init(self, user_input=None):
        """Manage options."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PASSWORD,
                        default=self.config_entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
            errors=errors,
        )
