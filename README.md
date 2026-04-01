# Naturela Smarthome – Home Assistant Integratie

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Stuur je **Naturela BurnerTouch pelletkachel** aan vanuit Home Assistant — via de bestaande cloud-API van [iot.naturela-bg.com](https://iot.naturela-bg.com). Geen lokale modificaties nodig.

---

## Ondersteunde apparaten

| Apparaat | Controller | Firmware |
|---|---|---|
| Naturela pelletbrander | BurnerTouch (NPBC_V6T_2) | ≥ 65 |

---

## Functies

### Climate entiteit
- Kachel **aan/uit** zetten
- **Doeltemperatuur** instellen (30–85 °C)
- Dynamische **kleurfeedback** in het dashboard:
  - 🟡 Amber = Ontsteking bezig (status 1)
  - 🟠 Diep-oranje = Kachel brandt (status 2 / 8)
  - Grijs = Stand-by / Uit

### Sensoren

| Entiteit | Type | Eenheid | Omschrijving |
|---|---|---|---|
| Keteltemperatuur | `sensor` | °C | Huidig ketelwater |
| Doeltemperatuur | `sensor` | °C | Ingestelde setpoint |
| Rookgastemperatuur | `sensor` | °C | Schoorsteen/flue |
| Warmwatertemperatuur | `sensor` | °C | Boiler DHW |
| Brandertrap | `sensor` | — | Branderstand (1–5, geheel getal) |
| Thermisch vermogen | `sensor` | kW | Werkelijk thermisch uitvermogen |
| Vlamniveau | `sensor` | 0–5 | Brandintensiteit |
| Pelletverbruik | `sensor` | kg | Totaal verbruik |
| Statuscode | `sensor` | — | Numerieke statuscode |

### Binary sensoren

| Entiteit | Omschrijving |
|---|---|
| CV-pomp | Aan/uit |
| Warmwaterpomp | Aan/uit |
| Ontsteking actief | Aan/uit |
| Reiniger actief | Aan/uit |
| Thermostaat | Invoer actief |
| Externe stop | Invoer actief |

### Statuscodes

| Code | Naam | Betekenis |
|---|---|---|
| 0 | Stand-by | Kachel inactief |
| 1 | Ontsteking | Opstartfase – pellets ontbranden |
| 2 | Werkt | Normale werking |
| 3   | Ontsteking     | Opstartfase fase 2 (Igniter=True)                    |
| 4 | Fout | Storing |
| 5 | Wachten | Wacht op startsignaal |
| 6 | Reinigen | Automatisch reinigingsprogramma |
| 8 | Werkt | Normale werking (alternatieve code) |
| 7   | Afkoelen       | Afkoelfase na afsluiting (FPower nog actief)         |
| 10  | Op temperatuur | Eindfase afkoeling (FPower=0)                        |

---

## Installatie

### Via HACS (aanbevolen)

1. Ga in Home Assistant naar **HACS → Integraties**
2. Klik op de drie puntjes rechtsboven → **Aangepaste repositories**
3. Voeg toe: `https://github.com/cjjagtenberg/naturela_smarthome` als type **Integration**
4. Zoek op **Naturela Smarthome** en installeer
5. **Herstart Home Assistant**
6. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen** → zoek **Naturela Smarthome**

### Handmatig

1. Download de map `custom_components/naturela_smarthome` uit deze repository
2. Kopieer naar je HA-configuratiemap:

```
<config>/custom_components/naturela_smarthome/
```

3. **Herstart Home Assistant**
4. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen** → zoek **Naturela Smarthome**

---

## Configuratie

Bij het instellen vul je in:

| Veld | Voorbeeld | Omschrijving |
|---|---|---|
| E-mailadres | `naam@mail.nl` | Inloggegevens van iot.naturela-bg.com |
| Wachtwoord | `••••••••` | Wachtwoord van iot.naturela-bg.com |
| Apparaat-ID | `6548` | Zichtbaar in de URL: `/#/device/burnertouch/6548` |
| Poll-interval | `30` | Verversing in seconden (standaard 30) |

---

## Dashboard kaart

Er is een speciale Lovelace custom card beschikbaar: [`naturela-pellet-card.js`](naturela-pellet-card.js).

**Installatie:**
1. Kopieer `naturela-pellet-card.js` naar `/config/www/` in Home Assistant
2. Voeg toe als resource: `Instellingen → Dashboard → Resources → + Toevoegen`
   - URL: `/local/naturela-pellet-card.js`
   - Type: JavaScript module
3. Voeg de kaart toe aan je Lovelace dashboard:

```yaml
type: custom:naturela-pellet-card
climate_entity: climate.schuurkachel
temp_sensor: sensor.schuurkachel_keteltemperatuur
flue_sensor: sensor.schuurkachel_rookgastemperatuur
power_sensor: sensor.schuurkachel_thermisch_vermogen
ch_pump_sensor: binary_sensor.schuurkachel_cv_pomp
dhw_pump_sensor: binary_sensor.schuurkachel_warmwaterpomp
status_sensor: sensor.schuurkachel_status
```

**Voorbeeld weergave:**

```
┌─────────────────────────────────────────┐
│  🔥  Pellet CV-kachel      Stand-by     │
│      Ketelwater: 42 °C  Instelling 60°C │
│  [ Aan ]  [████ UIT ████]               │
├──────────────┬──────────────┬─────────┤
│ SCHOORSTEEN  │   VERMOGEN   │   POMP    │
│    31 °C     │   17.9 kW    │  Actief   │
├──────────────┴──────────────┴─────────┤
│            STATUS: Stand-by             │
└─────────────────────────────────────────┘
```

---

## Hoe werkt het?

De integratie logt in op `iot.naturela-bg.com` via het normale webformulier (met CSRF-tokenextractie). Daarna wordt elke X seconden de API gepolld:

- **GET** `https://iot.naturela-bg.com/api/burnertouch/{device_id}` — haalt alle sensordata op
- **POST** `https://iot.naturela-bg.com/api/burnertouch/setState` — stuurt aan/uit-commando's en temperatuurwijzigingen

De integratie detecteert opstart via de `_command_pending` vlag: zolang de kachel nog niet in een actieve status staat na een aan-commando, wordt de UI optimistisch op "Verwarmen" gehouden zodat de gebruiker geen fout ziet.

---

## Changelog

### v11 (2026-04-01)
- Card: statische headerkleur (niet langer afhankelijk van status-kleur)
- Card: STATUS_COLORS aangevuld met statussen 3, 7 en 10

### v11 (2026-03-28)
- Card: pomptegel en thermisch vermogen samengevoegd
- Card: power_sensor hernoemd naar thermisch_vermogen

### v10 en eerder
- Python integratie: binary sensoren toegevoegd
- Python integratie: Firing/keeping string statussen toegevoegd aan ACTIVE_STATUSES
- Python integratie: brandertrap-power berekening via FPower-drempels

## Bekende beperkingen

- Vereist een actieve internetverbinding (cloud-gebaseerd)
- Timer-modus (`State = 2`) is niet instelbaar via HA
- De exacte betekenis van sommige statusvelden is gebaseerd op reverse engineering; feedback welkom

---

## Bijdragen

Pull requests en issues zijn welkom op [github.com/cjjagtenberg/naturela_smarthome](https://github.com/cjjagtenberg/naturela_smarthome). Heb jij een BurnerTouch-kachel met andere statuscodes of gedrag? Open een issue!

---

## Licentie

MIT — zie [LICENSE](LICENSE)
