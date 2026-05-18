"""Constants for the MyAir3 integration."""

from homeassistant.components.climate import HVACMode
from homeassistant.const import Platform

# Core Integration Constants
DOMAIN = "myair3"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

DEFAULT_PASSWORD = "password"
DEFAULT_SCAN_INTERVAL = 30

# MyAir3 API Mappings (from HA to API integer codes)
MODE_TO_MYAIR3 = {
    HVACMode.COOL: 1,
    HVACMode.HEAT: 2,
    HVACMode.FAN_ONLY: 3,
}

# MyAir3 API Fan Speed Mappings (from HA to API integer codes)
FAN_MODE_TO_MYAIR3 = {
    "low": 1,
    "medium": 2,
    "high": 3,
}
