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
  - Grey = Standby / Off

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

### Timer and schedule (v1.4.0+)

| Entity | Type | Description |
|---|---|---|
| Delay | `number` | Hours (0 to 24, step 0.25) until the stove turns on with *Start timer* (0 = now) |
| Burn duration | `number` | Hours (0.5 to 12) the stove burns before it turns off again |
| Start timer | `button` | Turn on after the delay, then off after the burn duration |
| Burn for duration | `button` | Turn on now, turn off after the burn duration |
| Turn off after duration | `button` | Turn off after the burn duration (stove already running) |
| Cancel schedule | `button` | Remove all planned on/off moments |
| Turn on at / Turn off at | `datetime` | Plan a one-off on or off moment |
| Scheduled on / Scheduled off | `sensor` | Next planned moment (timestamp) |

Services (target the climate entity): `naturela_smarthome.start_timer` (`delay`, `duration`), `turn_off_in`, `turn_on_for` (`duration`), `turn_on_at`, `turn_off_at` (`datetime`) and `cancel_schedule`.

```yaml
action: naturela_smarthome.start_timer
target:
  entity_id: climate.pellet_stove
data:
  delay: "01:30:00"
  duration: "03:00:00"
```

```yaml
action: naturela_smarthome.turn_on_at
target:
  entity_id: climate.pellet_stove
data:
  datetime: "2026-10-30 16:00:00"
```

- The schedule is stored and survives a Home Assistant restart. Moments that passed while HA was down are discarded (logged as a warning), not executed late.
- Turning the stove off via HA cancels a pending turn-off, unless a turn-on is still planned.
- Times without a time zone are interpreted in HA's configured time zone.

### Status codes

The status sensor shows the literal labels of the Naturela `BurnStatus` enum, exactly as the Naturela web portal (iot.naturela-bg.com) uses them. No own names or translations.

| Code | Label |
|---|---|
| 0 | Standby |
| 1 | Clearing |
| 2 | Charging |
| 3 | Firing |
| 4 | Burning |
| 5 | Keeping |
| 6 | Power1 |
| 7 | Power2 |
| 8 | Power3 |
| 9 | Clearing2 |
| 10 | StopFiring |

Observed on a BurnerTouch: start `Clearing → Charging → Firing → Burning → Power3`, stop `StopFiring → Clearing → Standby`. Unknown codes show as `Unknown` and are logged once as a warning.

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
| Device ID | `1234` | Visible in the URL: `/#/device/burnertouch/1234` |
| Poll interval | `30` | Refresh interval in seconds (default 30) |

---

## Dashboard card

A custom Lovelace card is available: [`naturela-pellet-card.js`](www/naturela-pellet-card.js).

Since card v34 the card has a collapsible **Timer** section (delay, burn duration, start / cancel). It finds the timer entities automatically on the same device as `climate_entity` (integration v1.4.1 or newer). While the stove is burning it only offers "turn off in"; while a timer is planned it shows the planned moments and a cancel button. Labels follow the HA language (Dutch or English).

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
│ 🔥 Pellet Stove          Standby        │
│ Boiler: 42 °C            Target 60°C   │
│         [ On  ]  [████  OFF  ████]      │
├──────────────┬──────────────┬──────────┤
│    FLUE      │    POWER     │   PUMP   │
│   31 °C      │   17.9 kW   │  Active  │
├──────────────┴──────────────┴──────────┤
│ STATUS: Standby                         │
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

#### v1.4.2 (2026-10-30)
- Status sensor now uses the literal Naturela `BurnStatus` labels (Standby, Clearing, Charging, Firing, Burning, Keeping, Power1/2/3, Clearing2, StopFiring). Previous labels were partly wrong (e.g. code 3 *Firing* was shown as "Cool down").
- Power1/2/3 are direct status codes 6/7/8; the derivation from `FPower` thresholds is removed
- **Breaking:** automations or templates that compare the status sensor with old labels (e.g. `Stand-by`, `Cool down`) must use the new labels

#### v1.4.1 (2026-10-30)
- Delay (`number`) and *Start timer* (`button`): turn on after a delay, off after the burn duration
- New service `start_timer` (`delay`, `duration`)

#### v1.4.0 (2026-10-30)
- Timer and schedule: turn off in X hours, burn for X hours, turn on/off at a set date and time
- New entities: burn duration (`number`), three `button`s, two `datetime`s and two timestamp `sensor`s
- New services: `turn_off_in`, `turn_on_for`, `turn_on_at`, `turn_off_at`, `cancel_schedule`
- Schedule persisted across restarts; Dutch and English translations

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

#### v38 (2026-10-30)
- Status shown as the literal label from the status sensor; colour by phase

#### v34 to v37 (2026-10-30)
- Collapsible Timer section with delay and burn duration steppers, start, turn off in, cancel
- Context aware: burning stove shows "turn off in", planned timer shows the planned moments

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
