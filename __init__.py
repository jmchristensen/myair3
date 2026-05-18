"""Simplified MyAir3 Integration for Home Assistant."""

from datetime import timedelta
import logging

import aiohttp
from defusedxml.ElementTree import fromstring

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .device_registry import async_setup_device_registry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyAir3 from config entry."""
    host = entry.data[CONF_HOST]
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = MyAir3Coordinator(hass, host, password, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await async_setup_device_registry(hass, entry.entry_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if config_entry.version == 1:
        new_data = {**config_entry.data}
        if CONF_PASSWORD not in new_data:
            new_data[CONF_PASSWORD] = DEFAULT_PASSWORD
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )
        _LOGGER.info("Migration to version %s successful", config_entry.version)
    return True


class MyAir3Coordinator(DataUpdateCoordinator):
    """Fetches MyAir3 data."""

    def __init__(self, hass: HomeAssistant, host: str, password: str, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        """Initialize."""
        self.host = host
        self.password = password
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch system data and all zones."""
        try:
            await self._fetch_xml(f"http://{self.host}/login?password={self.password}")

            sys_xml = await self._fetch_xml(f"http://{self.host}/getSystemData")
            sys_root = fromstring(sys_xml.encode("utf-8"))
            unitcontrol = sys_root.find(".//unitcontrol")

            if unitcontrol is None:
                raise UpdateFailed("No unitcontrol data in response")

            num_zones = int(unitcontrol.findtext("numberOfZones", "0") or "0")

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

    async def _async_set_data(self, url: str, description: str) -> None:
        """Send command and refresh data."""
        resp = await self._fetch_xml(url)
        if "<ack>1</ack>" in resp:
            await self.async_refresh()
        else:
            _LOGGER.warning("ack not returned for %s", description)
            await self.async_request_refresh()

    async def set_system_power(self, power: int) -> None:
        """Turn system on/off. 0=off, 1=on."""
        await self._async_set_data(
            f"http://{self.host}/setSystemData?airconOnOff={power}", "set_system_power"
        )

    async def set_system_temp(self, temp: float) -> None:
        """Set system target temperature."""
        await self._async_set_data(
            f"http://{self.host}/setSystemData?centralDesiredTemp={temp}",
            "set_system_temp",
        )

    async def set_fan_speed(self, speed: int) -> None:
        """Set fan speed. 1=low, 2=medium, 3=high."""
        await self._async_set_data(
            f"http://{self.host}/setSystemData?fanSpeed={speed}", "set_fan_speed"
        )

    async def set_zone_power(self, zone: int, power: int) -> None:
        """Turn zone on/off. 0=off, 1=on."""
        await self._async_set_data(
            f"http://{self.host}/setZoneData?zone={zone}&zoneSetting={power}",
            "set_zone_power",
        )

    async def set_zone_temp(self, zone: int, temp: float) -> None:
        """Set zone target temperature."""
        setting = self.data["zones"][zone]["setting"]
        await self._async_set_data(
            f"http://{self.host}/setZoneData?zone={zone}&desiredTemp={temp}&zoneSetting={setting}",
            "set_zone_temp",
        )

    async def set_hvac_mode(self, mode: int) -> None:
        """Set system mode. 1=cool, 2=heat, 3=fan only."""
        await self._async_set_data(
            f"http://{self.host}/setSystemData?mode={mode}", "set_hvac_mode"
        )
