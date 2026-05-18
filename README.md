# Naturela Smarthome – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Control your **Naturela BurnerTouch pellet stove** from Home Assistant — via the existing cloud API at [iot.naturela-bg.com](https://iot.naturela-bg.com). No local modifications required.

---

## Supported devices

| Device | Controller | Firmware |
|---|---|---|
| Naturela pellet burner | BurnerTouch (NPBC_V6T_2) | ≥ 65 |

---

## Features

### Climate entity
- Turn the stove **on/off**
- Set the **target temperature** (30–85 °C)
- Dynamic **colour feedback** in the dashboard:
  - 🟡 Amber = Ignition in progress (status 1)
  - 🟠 Deep orange = Stove burning (status 2 / 8)
  - Grey = Stand-by / Off

### Sensors

| Entity | Type | Unit | Description |
|---|---|---|---|
| Boiler temperature | `sensor` | °C | Current boiler water temperature |
| Target temperature | `sensor` | °C | Configured setpoint |
| Flue gas temperature | `sensor` | °C | Chimney / flue |
| DHW temperature | `sensor` | °C | Domestic hot water boiler |
| Burner step | `sensor` | — | Burner level (1–5, integer) |
| Thermal output | `sensor` | kW | Actual thermal output power |
| Flame level | `sensor` | 0–5 | Combustion intensity |
| Pellet consumption | `sensor` | kg | Total consumption |
| Status | `sensor` | — | Human-readable status label |

### Binary sensors

| Entity | Description |
|---|---|
| Central heating pump | On/off |
| DHW pump | On/off |
| Igniter active | On/off |
| Cleaner active | On/off |
| Thermostat | Input active |
| External stop | Input active |

### Status codes

| Code | Name | Meaning |
|---|---|---|
| 0 | Stand-by | Stove inactive |
| 1 | Cleaning | Start phase – pellets igniting |
| 2 | Burning | Normal operation |
| 3 | Unfolding fire | Flame build-up after ignition (flue gas +5 °C trigger) |
| 4 | Fault | Error / alarm |
| 5 | Suspend | Waiting for start signal |
| 6 | Suspend | Entering suspend (P1 modulation just before) |
| 7 | Burning shutdown | Ramp-down phase (P3→P2→P1, 60 s each) |
| 8 | Burning | Normal operation (alternative code) |
| 10 | Cool down | Final cool-down phase (FPower=0) |

---

## Installation

### Via HACS (recommended)

1. In Home Assistant go to **HACS → Integrations**
2. Click the three dots in the top right → **Custom repositories**
3. Add: `https://github.com/cjjagtenberg/naturela_smarthome` as type **Integration**
4. Search for **Naturela Smarthome** and install
5. **Restart Home Assistant**
6. Go to **Settings → Devices & services → Add integration** → search **Naturela Smarthome**

### Manual

1. Download the `custom_components/naturela_smarthome` folder from this repository
2. Copy it to your HA configuration directory:
   ```
   <config>/custom_components/naturela_smarthome/
   ```
3. **Restart Home Assistant**
4. Go to **Settings → Devices & services → Add integration** → search **Naturela Smarthome**

---

## Configuration

During setup you will be asked for:

| Field | Example | Description |
|---|---|---|
| Email address | `name@mail.com` | Login credentials for iot.naturela-bg.com |
| Password | `••••••••` | Password for iot.naturela-bg.com |
| Device ID | `6548` | Visible in the URL: `/#/device/burnertouch/6548` |
| Poll interval | `30` | Refresh interval in seconds (default 30) |

---

## Dashboard card

A custom Lovelace card is available: [`naturela-pellet-card.js`](www/naturela-pellet-card.js).

**Installation:**

1. Copy `naturela-pellet-card.js` to `/config/www/` in Home Assistant
2. Add as a resource: `Settings → Dashboards → Resources → + Add`
   - URL: `/local/naturela-pellet-card.js`
   - Type: JavaScript module
3. Add the card to your Lovelace dashboard:

```yaml
type: custom:naturela-pellet-card
climate_entity: climate.pellet_stove
boiler_sensor: sensor.pellet_stove_boiler_temperature
flue_sensor: sensor.pellet_stove_flue_gas_temperature
power_sensor: sensor.pellet_stove_thermal_output
status_sensor: sensor.pellet_stove_status
alarm_sensor: sensor.pellet_stove_alarm
```

**Example view:**
```
┌─────────────────────────────────────────┐
│ 🔥 Pellet Stove          Stand-by       │
│ Boiler: 42 °C            Target 60°C   │
│         [ On  ]  [████  OFF  ████]      │
├──────────────┬──────────────┬──────────┤
│    FLUE      │    POWER     │   PUMP   │
│   31 °C      │   17.9 kW   │  Active  │
├──────────────┴──────────────┴──────────┤
│ STATUS: Stand-by                        │
└─────────────────────────────────────────┘
```

---

## How it works

The integration logs in to `iot.naturela-bg.com` via the standard web form (with CSRF token extraction). Every X seconds the API is polled:

- **GET** `https://iot.naturela-bg.com/api/burnertouch/{device_id}` — fetches all sensor data
- **POST** `https://iot.naturela-bg.com/api/burnertouch/setState` — sends on/off commands and temperature changes

The integration detects start-up via the `_command_pending` flag: as long as the stove has not entered an active status after an on-command, the UI is optimistically held at "Heating" so the user does not see a false off state.

---

## Changelog

### Integration

#### v1.3.1 (2026-05-18)
- Full English translation: README, sensor friendly names, binary sensor names, `strings.json`
- Added `sensor.pellet_stove_alarm` exposing the controller's `ErrorFlag` as a human-readable fault state
- Added `close()` method to `NaturelaAPI` for clean aiohttp session teardown — fixes the `AttributeError: 'NaturelaAPI' object has no attribute 'close'` during config flow (#1)
- `_safe_temp()` prevents NaN values for boiler and target temperature
- Coordinator now supports both `hass.data[DOMAIN][entry.entry_id]` and `entry.runtime_data` lookup
- Card: status handling refactor, header layout tweaks, syntax fixes
- `manifest.json` field ordering normalised

#### v1.3.0 (2026-04-26)
- Status sensor now uses `SensorDeviceClass.ENUM` with literal Naturela BurnerTouch controller labels (`Stand-by`, `Cleaning`, `Unfolding fire`, `Burning`, `Power1/2/3`, `Suspend`, `Burning shutdown`, `Cool down`)
- Power level derivation: `Burning` is split into `Power1` / `Power2` / `Power3` based on `FPower` vs threshold values reported by the API
- WARNING log (once per unique value) for unknown Status values, to capture real-world alarm spellings

#### v1.2.2 (2026-04-26)
- Fix sensor entities going `unavailable` after setup: `sensor.py` now reads the coordinator from `hass.data[DOMAIN][entry.entry_id]` instead of the unsupported `entry.runtime_data`

#### v1.2.1 (2026-04-26)
- Fix `turn_on`/`turn_off`: `_do_post` no longer accidentally `async`
- Fix thermal output display: show `0 kW` instead of `-` when `OutputPower` is null in standby/ignition

#### v1.2.0 (2026-04-26)
- NaN-safety for numeric sensors (`_coerce_numeric()` filters NaN/Infinity/null)
- Re-login on session expiry — ON commands no longer silently lost
- `climate.turn_on` / `turn_off` feature flags added
- Status 7 ("Cool down") and 10 ("Suspend") names added
- Power 1 / 2 / 3 derivation from `FPower` thresholds
- Burner step (FPower) vs Thermal output (OutputPower×0.1) split into two sensors
- ErrorFlag display with specific error names
- Default `scan_interval` set to 10 seconds

#### v1.0.0 (2026-03-27)
- Initial release: climate entity, sensors, binary sensors, config flow UI, Lovelace custom card, 60+ language translations

### Card

#### v11 (2026-04-01)
- Static header colour (no longer dependent on status colour)
- `STATUS_COLORS` extended with statuses 3, 7 and 10

#### v11 (2026-03-28)
- Pump tile and thermal output merged
- `power_sensor` renamed to `thermal_output`

#### v10 and earlier
- Python integration: binary sensors added
- Python integration: Firing/keeping string statuses added to `ACTIVE_STATUSES`
- Python integration: burner step / power calculation via `FPower` thresholds

---

## Known limitations

- Requires an active internet connection (cloud-based)
- Timer mode (`State = 2`) cannot be configured via HA
- The exact meaning of some status fields is based on reverse engineering; feedback welcome

---

## Contributing

Pull requests and issues are welcome at [github.com/cjjagtenberg/naturela_smarthome](https://github.com/cjjagtenberg/naturela_smarthome).

Do you have a BurnerTouch stove with different status codes or behaviour? Open an issue!

---

## License

MIT — see [LICENSE](LICENSE)
