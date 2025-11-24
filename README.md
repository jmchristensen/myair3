# MyAir3 Home Assistant Integration

Control your Advantage Air MyAir3 air conditioning system from Home Assistant. If you have a newer system, MyAir5, MyLights etc, use the (much better) Advantage Air integration that is bundled with Home Assistant.

## Features

- **System Control**: Turn on/off, set target temperature, control fan speed (low/medium/high)
- **Zone Control**: Individual temperature and on/off control for each zone
- **Damper Position Monitoring**: See damper positions for each zone
- **Battery Detection**: Automatic detection when zone temperature sensors have low batteries
- **Fallback Mode**: When a temperature sensor fails, automatically fall back to damper percentage control
- **Real-time Updates**: Polls system every 30 seconds for latest data
- This system does not create or modify the schedules/timers/programs in the MyAir3 system. The expectation for now is to create a helper schedule/automations within Home Assistant for greater flexibility
- This integration has not been tested against a multi-unit HVAC setup (as I only have a single unit). Its unknown how this integration will respond to such a setup. 

## Installation

### Manual Installation

1. Download or clone this repository
2. Copy the `myair3` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

### Installation via HACS

Coming soon... possibly never. Who knows!

## Configuration

1. Go to Settings → Devices & Services → Create Integration
2. Search for "MyAir3"
3. Enter your Advantage Air MyAir3 system's IP address
4. Click Submit

The system will be added with:
- One main system climate entity
- One climate entity per zone
- One damper sensor per zone (only enabled when temperature sensor has low/no battery)

## Entities

### System Level

- **Climate Entity**: "System" - Main HVAC control
  - Power (On/Off)
  - Target Temperature
  - Fan Speed (Low/Medium/High)
  - Current Temperature

### Zone Level

- **Climate Entity**: Zone name (e.g., "Living Room") - Zone temperature control
  - Power (On/Off)
  - Target Temperature
  - Current Temperature (with fallback to damper percentage if sensor unavailable)

- **Sensor Entity**: "{Zone Name} Damper" - Damper position percentage
  - Only available when temperature sensor has low/no battery

## Troubleshooting

### Integration won't connect

- Verify the IP address is correct
- Ensure your MyAir3 system is on the same network as Home Assistant
- Check that the system is accessible at `http://<IP>/getSystemData`

### Temperature sensor shows 30°C when battery is low

This is expected behavior (for now). The system will:
1. Show the damper position sensor (as a percentage)
2. Use the damper percentage (mapped to 15-30°C range) for temperature control
3. You can still control the zone by adjusting the target temperature

### Diagnostics

For troubleshooting, enable diagnostics:
1. Go to Settings → Devices & Services → MyAir3 System
2. Click the three dots menu
3. Select "Download diagnostics"

This will provide system state, zone information, and connection details.

## Advanced

### API Endpoints Used

- `GET /getSystemData` - System status and configuration
- `GET /getZoneData?zone=N` - Individual zone data
- `GET /setSystemData?...` - Update system settings
- `GET /setZoneData?...` - Update zone settings

All communication is done via HTTP GET with XML responses (legacy myair format).

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
ruff check custom_components/myair3/
```

## Compatibility

- **Home Assistant**: 2025.11+
- **MyAir3**: Legacy XML API version
- **Network**: System must be reachable via HTTP on local network

## License

MIT

## Support

For issues or feature requests, please create an issue on GitHub.