# Naturela Smarthome – Home Assistant Integratie

Een custom Home Assistant integratie voor de **Naturela BurnerTouch** pelletkachel, via de cloud-API op [iot.naturela-bg.com](https://iot.naturela-bg.com).

## Functies

- **Climate-entiteit** – aan/uit schakelen en doeltemperatuur instellen
- **Sensoren** – aanvoer- en retourtemperatuur, rookgastemperatuur, vermogen, vuurniveau, brandstofverbruik, ventilatortoerental
- **Binaire sensoren** – CV-pomp, warmwaterpomp, ontsteking, reiniger, thermostaat, externe stop
- **Statusvertaling** – leesbare kacheltoestand in het Nederlands

## Installatie

### Via HACS (aanbevolen)

1. Voeg deze repo toe als custom repository in HACS: `https://github.com/cjjagtenberg/naturela_smarthome`
2. Installeer "Naturela Smarthome"
3. Herstart Home Assistant

### Handmatig

1. Kopieer de map `custom_components/naturela_smarthome` naar je HA `config/custom_components/` map
2. Herstart Home Assistant

## Configuratie

1. Ga naar **Instellingen → Integraties → Integratie toevoegen**
2. Zoek op **Naturela Smarthome**
3. Vul in:
   - E-mailadres (van iot.naturela-bg.com account)
   - Wachtwoord
   - Apparaat-ID (staat in de URL: `/device/burnertouch/{ID}`)
   - Poll-interval in seconden (standaard 30, minimum 10)

## Entiteiten

| Entiteit | Type | Beschrijving |
|---|---|---|
| `climate.schuurkachel` | Climate | Aan/uit + doeltemperatuur |
| `sensor.schuurkachel_status` | Sensor | Huidige kachelstatus |
| `sensor.schuurkachel_aanvoertemperatuur` | Sensor | Aanvoerwater temperatuur (°C) |
| `sensor.schuurkachel_retourtemperatuur` | Sensor | Retourwater temperatuur (°C) |
| `sensor.schuurkachel_rookgastemperatuur` | Sensor | Rookgastemperatuur (°C) |
| `sensor.schuurkachel_omgevingstemperatuur` | Sensor | Omgevingstemperatuur (°C) |
| `sensor.schuurkachel_vermogen` | Sensor | Ingesteld vermogenspercentage (%) |
| `sensor.schuurkachel_vuurniveau` | Sensor | Vuurniveau (0–5) |
| `sensor.schuurkachel_brandstofverbruik` | Sensor | Brandstofverbruik (kg) |
| `sensor.schuurkachel_ventilator` | Sensor | Verbrandingsluchtventilator (RPM) |
| `binary_sensor.schuurkachel_cv_pomp` | Binair | CV-pomp actief |
| `binary_sensor.schuurkachel_warmwaterpomp` | Binair | Warmwaterpomp actief |
| `binary_sensor.schuurkachel_ontsteking` | Binair | Ontsteking actief |

## Apparaatinfo

- Hardware: NPBC\_V6T\_2
- Firmware: 65/31
- Verbinding: cloud polling via `/api/burnertouch/{device_id}`

## Licentie

MIT
