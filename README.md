# Naturela Smarthome — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/cjjagtenberg/naturela_smarthome)](https://github.com/cjjagtenberg/naturela_smarthome/releases)

Control your **Naturela BurnerTouch pellet stove** from Home Assistant — using the existing cloud API at [iot.naturela-bg.com](https://iot.naturela-bg.com). No local modifications or hurdware needed.

---

## 📺 Screenshot

![Naturela card in Home Assistant](https://raw.githubusercontent.com/cjjagtenberg/naturela_smarthome/main/docs/screenshot.png)

---

## ✅ Supported devices

| Device | Controller | Notes |
|---|---|---|
| Naturela pellet burner | BurnerTouch (NPBC_V6T_2) | Tested with firmware ≥ 65 |

> Other BurnerTouch models may work. Open an [issue](https://github.com/cjjagtenberg/naturela_smarthome/issues) if you have a different model.

---

## 🚀 Features

### Climate entity
- Turn stove **on / off**
- Set **target temperature** (30–85 °C)
- Reports **current boiler temperature**
- Dynamic **status colour** in the dashboard

### Sensors

| Entity | Type | Unit | Description |
|---|---|---|---|
| Boiler temperature | `sensor` | °C | Current boiler water temperature |
| Target temperature | `sensor` | °C | Current setpoint |
| Flue gas temperature | `sensor` | °C | Chimney / flue temperature |
| DHW temperature | `sensor` | °C | Domestic hot water boiler |
| Power output | `sensor` | kW | Current combustion power |
| Flame level | `sensor` | 0–5 | Combustion intensity |
| Pellet consumption | `sensor` | kg | Total pellet usage |
| Output level | `sensor` | % | Output power percentage |
| Status code | `sensor` | — | Numeric status code |

### Binary sensors

| Entity | Description |
|---|---|
| CH pump | Central heating pump on/off |
| DHW pump | Hot water pump on/off |
| Ignition active | Ignition in progress |
| Cleaning active | Self-clean cycle running |

---

## 📦 Installation

### Option 1 — HACS (recommended)

1. Open **HACS** → **Integrations** → click the three-dot menu (⋮) → **Custom repositories**
2. Add `https://github.com/cjjagtenberg/naturela_smarthome` as an **Integration**
3. Search for **"Naturela"** and click **Download**
4. Restart Home Assistant

### Option 2 — Manual

1. Download or clone this repository
2. Copy the `custom_components/naturela_smarthome/` folder to your HA config directory:
   ```
   <config>/custom_components/naturela_smarthome/
   ```
3. Restart Home Assistant

---

## ⚙️ Configuration

After installation and restart:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Naturela"**
3. Fill in:

   | Field | Description |
   |---|---|
   | **Email address** | Your login email for iot.naturela-bg.com |
   | **Password** | Your password |
   | **Device ID** | The numeric ID from the URL when logged in: `…/device/burnertouch/`**`6548`** |
   | **Poll interval** | How often to refresh (seconds, 10–300, default 30) |

> **Finding your Device ID:** Log in at [iot.naturela-bg.com](https://iot.naturela-bg.com), click on your device, and look at the URL — the number at the end is your Device ID.

---

## 🎴 Lovelace Card

A custom card is included for a rich one-card overview: `naturela-pellet-card.js`

### Install the card

1. Copy `naturela-pellet-card.js` to your HA `config/www/` folder
2. Go to **Settings → Dashboards → Resources** and add:
   - URL: `/local/naturela-pellet-card.js`
   - Type: **JavaScript module**
3. Reload the browser

### Add the card to your dashboard

```yaml
type: custom:naturela-pellet-card
title: Pellet stove
climate_entity: climate.schuurkachel
status_sensor: sensor.schuurkachel_status
boiler_sensor: sensor.schuurkachel_keteltemperatuur
flue_sensor: sensor.schuurkachel_rookgastemperatuur
power_sensor: sensor.schuurkachel_vermogen
flame_sensor: sensor.schuurkachel_vlamniveau
# alarm_sensor: sensor.schuurkachel_alarm   # optional
```

The card automatically changes colour based on the stove status:

| Colour | Status |
|---|---|
| 🟡 Amber | Igniting |
| 🟠 Deep orange | Running / heating |
| 🔵 Blue | Waiting |
| 🟤 Brown | Cleaning |
| 🔴 Red | Fault |
| ⬛ Dark grey | Stand-by / Off |

---

## 🌍 Translations

The configuration UI is translated into **55 languages**, including all languages officially supported by Home Assistant (English, Dutch, German, French, Spanish, Italian, Polish, Portuguese, Russian, Ukrainian, Chinese (Simplified + Traditional), Japanese, Korean, and many more).

---

## 🔧 Troubleshooting

### Temperature command not working
- Make sure the integration restarted after a code update — a **full HA restart** is required (reload config entry is not enough due to Python module caching)
- Check the HA logs: **Settings → System → Logs** and filter on `naturela`

### Status shows "unavailable"
- Verify your credentials are correct at [iot.naturela-bg.com](https://iot.naturela-bg.com)
- Check that your Device ID matches the URL

### Encoding issues (°C displays as "Â°C")
- Re-upload the card JS file and bump the Lovelace resource version number
- The included file is pure ASCII — if your editor re-saves with UTF-8, HTML entities (`&deg;`) are used to avoid encoding problems

---

## 🏗️ Architecture

```
naturela_smarthome/
├── __init__.py          # Integration setup, DataUpdateCoordinator
├── api.py               # Async HTTP client (login, poll, setTemp, setState)
├── climate.py           # Climate entity (on/off, setpoint)
├── sensor.py            # All numeric sensors
├── binary_sensor.py     # Boolean sensors (pump, ignition, cleaning)
├── config_flow.py       # UI configuration flow
├── const.py             # Constants and API URLs
├── manifest.json        # Integration metadata
├── strings.json         # Source strings (Dutch, used as fallback)
└── translations/        # 55 language files
    ├── en.json
    ├── nl.json
    └── … (53 more)
```

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss large changes.

- Keep the `api.py` communication layer separate from HA entities
- All text visible in the UI must have entries in `strings.json` and `translations/`
- Test with `hassfest` before submitting

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🇳🇱 Dutch / Nederlands

### Installatie via HACS

1. Open **HACS** → **Integraties** → drie-puntjes (⋮) → **Aangepaste repositories**
2. Voeg `https://github.com/cjjagtenberg/naturela_smarthome` toe als **Integratie**
3. Zoek naar **"Naturela"** en klik op **Downloaden**
4. Start Home Assistant opnieuw op

### Configuratie

Na de installatie en herstart:

1. Ga naar **Instellingen → Apparaten en diensten → Integratie toevoegen**
2. Zoek op **"Naturela"**
3. Vul in:
   - **E-mailadres** — je inloggegevens voor iot.naturela-bg.com
   - **Wachtwoord**
   - **Apparaat-ID** — het nummer achteraan de URL bij je apparaat: `.../device/burnertouch/`**`6548`**
   - **Poll-interval** — verversingsfrequentie in seconden (standaard 30)

### Lovelace kaart

Kopieer `naturela-pellet-card.js` naar `config/www/`, voed de resource toe via **Instellingen → Dashboards → Bronnen**, en gebruik de YAML hierboven om de kaart toe te voegen.
