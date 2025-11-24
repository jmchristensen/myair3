"""Simplified MyAir3 Integration for Home Assistant."""

from datetime import timedelta
import logging

import aiohttp
from defusedxml.ElementTree import fromstring

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS
from .device_registry import async_setup_device_registry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyAir3 from config entry."""
    host = entry.data[CONF_HOST]
    coordinator = MyAir3Coordinator(hass, host)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up device registry
    await async_setup_device_registry(hass, entry.entry_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class MyAir3Coordinator(DataUpdateCoordinator):
    """Fetches MyAir3 data."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize."""
        self.host = host
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        """Fetch system data and all zones."""
        try:
            # Authenticate first
            await self._fetch_xml(f"http://{self.host}/login?password=password")

            # Fetch system data
            sys_xml = await self._fetch_xml(f"http://{self.host}/getSystemData")
            sys_root = fromstring(sys_xml.encode("utf-8"))
            unitcontrol = sys_root.find(".//unitcontrol")

            if unitcontrol is None:
                raise UpdateFailed("No unitcontrol data in response")

            num_zones = int(unitcontrol.findtext("numberOfZones", "0") or "0")

            # Fetch each zone
            zones = {}
            for zone_id in range(1, num_zones + 1):
                zone_xml = await self._fetch_xml(
                    f"http://{self.host}/getZoneData?zone={zone_id}"
                )
                zone_root = fromstring(zone_xml.encode("utf-8"))
                zone_elem = zone_root.find(f".//zone{zone_id}")
                if zone_elem is not None:
                    has_low_batt = (
                        int(zone_elem.findtext("hasLowBatt", "0") or "0") == 1
                    )
                    zones[zone_id] = {
                        "name": zone_elem.findtext("name", f"Zone {zone_id}")
                        or f"Zone {zone_id}",
                        "setting": int(zone_elem.findtext("setting", "0") or "0"),
                        "desiredTemp": float(
                            zone_elem.findtext("desiredTemp", "20") or "20"
                        ),
                        "actualTemp": float(
                            zone_elem.findtext("actualTemp", "20") or "20"
                        ),
                        "userPercentSetting": int(
                            zone_elem.findtext("userPercentSetting", "0") or "0"
                        ),
                        "hasLowBatt": has_low_batt,
                        "tempSensorAvailable": not has_low_batt,
                    }

            return {
                "airconOnOff": int(unitcontrol.findtext("airconOnOff", "0") or "0"),
                "mode": int(unitcontrol.findtext("mode", "1") or "1"),
                "fanSpeed": int(unitcontrol.findtext("fanSpeed", "1") or "1"),
                "centralDesiredTemp": float(
                    unitcontrol.findtext("centralDesiredTemp", "20") or "20"
                ),
                "centralActualTemp": float(
                    unitcontrol.findtext("centralActualTemp", "20") or "20"
                ),
                "zones": zones,
            }
        except (OSError, ValueError) as err:
            raise UpdateFailed(f"Error: {err}") from err

    async def _fetch_xml(self, url: str) -> str:
        """Fetch and return XML response."""
        async with self.session.get(
            url, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"HTTP {resp.status}")
            return await resp.text()

    async def set_system_power(self, power: int) -> None:
        """Turn system on/off. 0=off, 1=on."""
        await self._fetch_xml(f"http://{self.host}/setSystemData?airconOnOff={power}")
        await self.async_request_refresh()

    async def set_system_temp(self, temp: float) -> None:
        """Set system target temperature."""
        await self._fetch_xml(
            f"http://{self.host}/setSystemData?centralDesiredTemp={temp}"
        )
        await self.async_request_refresh()

    async def set_fan_speed(self, speed: int) -> None:
        """Set fan speed. 1=low, 2=medium, 3=high."""
        await self._fetch_xml(f"http://{self.host}/setSystemData?fanSpeed={speed}")
        await self.async_request_refresh()

    async def set_zone_power(self, zone: int, power: int) -> None:
        """Turn zone on/off. 0=off, 1=on."""
        await self._fetch_xml(
            f"http://{self.host}/setZoneData?zone={zone}&zoneSetting={power}"
        )
        await self.async_request_refresh()

    async def set_zone_temp(self, zone: int, temp: float) -> None:
        """Set zone target temperature."""
        setting = self.data["zones"][zone]["setting"]
        await self._fetch_xml(
            f"http://{self.host}/setZoneData?zone={zone}&desiredTemp={temp}&zoneSetting={setting}"
        )
        await self.async_request_refresh()

    async def set_hvac_mode(self, mode: int) -> None:
        """Set system mode. 1=cool, 2=heat, 3=fan only."""
        await self._fetch_xml(f"http://{self.host}/setSystemData?mode={mode}")
        await self.async_request_refresh()
