/**
 * Naturela Pellet Stove Card  -  v10
 * Custom Lovelace card for the Naturela BurnerTouch pellet stove.
 *
 * Entiteiten (configureerbaar via card config):
 *   climate_entity  : climate.schuurkachel
 *   status_sensor   : sensor.schuurkachel_status
 *   boiler_sensor   : sensor.schuurkachel_keteltemperatuur
 *   flue_sensor     : sensor.schuurkachel_rookgastemperatuur
 *   power_sensor    : sensor.schuurkachel_vermogen
 *   ch_pump_sensor  : binary_sensor.schuurkachel_cv_pomp
 *   dhw_pump_sensor : binary_sensor.schuurkachel_warmwaterpomp
 *   alarm_sensor    : sensor.schuurkachel_alarm  (optioneel - storingstekst van display)
 */

const STATUS_COLORS = {
  1: { bg: '#FFA000', text: '#fff', name: 'Ontsteking' },   // amber
  2: { bg: '#E64A19', text: '#fff', name: 'Werkt' },        // deep-orange
  4: { bg: '#D32F2F', text: '#fff', name: 'Fout' },         // red
  5: { bg: '#1565C0', text: '#fff', name: 'Wachten' },      // blue
  6: { bg: '#6D4C41', text: '#fff', name: 'Reinigen' },     // brown
  8: { bg: '#E64A19', text: '#fff', name: 'Werkt' },        // same as 2
};
const STANDBY_COLOR = { bg: '#546E7A', text: '#fff', name: 'Stand-by' };
const OFF_COLOR     = { bg: '#37474F', text: '#aaa', name: 'Uit' };

// Sensor-waarden die als "geen storing" gelden
const ALARM_EMPTY = ['', 'none', 'geen', 'ok', 'unknown', 'unavailable', '-'];

class NaturelaPelletCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._pendingTemp   = null;
    this._pendingExpiry = null;
  }

  setConfig(config) {
    this._config = {
      climate_entity : config.climate_entity  || 'climate.schuurkachel',
      status_sensor  : config.status_sensor   || 'sensor.schuurkachel_status',
      boiler_sensor  : config.boiler_sensor   || 'sensor.schuurkachel_keteltemperatuur',
      flue_sensor    : config.flue_sensor     || 'sensor.schuurkachel_rookgastemperatuur',
      power_sensor   : config.power_sensor    || 'sensor.schuurkachel_vermogen',
      ch_pump_sensor : config.ch_pump_sensor  || 'binary_sensor.schuurkachel_cv_pomp',
      dhw_pump_sensor: config.dhw_pump_sensor || 'binary_sensor.schuurkachel_warmwaterpomp',
      alarm_sensor   : config.alarm_sensor    || null,
      title          : config.title           || 'Pelletkachel',
    };
  }

  set hass(hass) {
    this._hass = hass;
    // Wis pending temp als HA bevestigt of timer verlopen is
    if (this._pendingTemp !== null) {
      if (Date.now() > (this._pendingExpiry || 0)) {
        this._pendingTemp   = null;
        this._pendingExpiry = null;
      } else {
        const actual = parseFloat(this._targetTempFromHass());
        if (!isNaN(actual) && actual === this._pendingTemp) {
          this._pendingTemp   = null;
          this._pendingExpiry = null;
        }
      }
    }
    this._render();
  }

  /* -- helpers ------------------------------------------------------- */

  _stateObj(entity) {
    return entity ? this._hass?.states[entity] : null;
  }

  _statusCode() {
    const climate = this._stateObj(this._config.climate_entity);
    if (!climate) return null;
    const code = climate.attributes?.status;
    if (code !== undefined && code !== null) return parseInt(code, 10);
    if (climate.state === 'off') return 0;
    return null;
  }

  _colorForCode(code) {
    if (code === null || code === undefined) return STANDBY_COLOR;
    if (code === 0) return OFF_COLOR;
    return STATUS_COLORS[code] || STANDBY_COLOR;
  }

  _isOn() {
    const st = this._stateObj(this._config.climate_entity);
    return st && st.state !== 'off' && st.state !== 'unavailable';
  }

  _targetTempFromHass() {
    const st = this._stateObj(this._config.climate_entity);
    return st?.attributes?.temperature ?? '-';
  }

  _targetTemp() {
    if (this._pendingTemp !== null) return this._pendingTemp;
    return this._targetTempFromHass();
  }

  _currentTemp() {
    const boiler = this._stateObj(this._config.boiler_sensor);
    if (boiler && boiler.state !== 'unavailable') return parseFloat(boiler.state).toFixed(1);
    const st = this._stateObj(this._config.climate_entity);
    return st?.attributes?.current_temperature ?? '-';
  }

  _sensorVal(entity, decimals = 0) {
    const st = this._stateObj(entity);
    if (!st || st.state === 'unavailable' || st.state === 'unknown') return '-';
    const n = parseFloat(st.state);
    return isNaN(n) ? st.state : n.toFixed(decimals);
  }

  _sensorUnit(entity) {
    return this._stateObj(entity)?.attributes?.unit_of_measurement ?? '';
  }

  /**
   * Geeft de storingstekst terug als de alarm_sensor een betekenisvolle waarde heeft,
   * anders null.
   */
  _alarmText() {
    if (!this._config.alarm_sensor) return null;
    const st = this._stateObj(this._config.alarm_sensor);
    if (!st) return null;
    const val = (st.state ?? '').trim();
    if (ALARM_EMPTY.includes(val.toLowerCase())) return null;
    return val;
  }

  /* -- actions -------------------------------------------------------- */

  _callClimate(service, data) {
    this._hass.callService('climate', service, {
      entity_id: this._config.climate_entity,
      ...data,
    });
  }

  _turnOn()  { this._callClimate('set_hvac_mode', { hvac_mode: 'heat' }); }
  _turnOff() { this._callClimate('set_hvac_mode', { hvac_mode: 'off'  }); }

  _adjustTemp(delta) {
    // Gebruik _targetTemp() zodat snelle klikken correct optellen
    const cur = parseFloat(this._targetTemp());
    if (isNaN(cur)) return;
    const climate = this._stateObj(this._config.climate_entity);
    const minTemp = climate?.attributes?.min_temp ?? 30;
    const maxTemp = climate?.attributes?.max_temp ?? 85;
    const newTemp = Math.min(maxTemp, Math.max(minTemp, cur + delta));
    this._pendingTemp   = newTemp;
    this._pendingExpiry = Date.now() + 8000;
    this._render();
    this._callClimate('set_temperature', { temperature: newTemp });
  }

  /* -- render --------------------------------------------------------- */

  _render() {
    if (!this._hass || !this._config) return;

    const code      = this._statusCode();
    const color     = this._colorForCode(code);
    const isOn      = this._isOn();
    const target    = this._targetTemp();
    const actual    = this._currentTemp();
    const alarmText = this._alarmText();

    // Banner tonen als: status = Fout (4) OF alarm_sensor heeft een waarde
    const isFault   = code === 4 || alarmText !== null;
    const bannerMsg = alarmText
      ? alarmText
      : 'Storing gedetecteerd - controleer de kachel';

    const flueVal  = this._sensorVal(this._config.flue_sensor);
    const flueUnit = this._sensorUnit(this._config.flue_sensor);
    const powVal   = this._sensorVal(this._config.power_sensor, 1);
    const powUnit  = this._sensorUnit(this._config.power_sensor);
    const chPumpSt  = this._stateObj(this._config.ch_pump_sensor)?.state;
    const chPumpVal = chPumpSt === 'on' ? 'Aan' : chPumpSt === 'off' ? 'Uit' : '-';
    const dhwPumpSt  = this._stateObj(this._config.dhw_pump_sensor)?.state;
    const dhwPumpVal = dhwPumpSt === 'on' ? 'Aan' : dhwPumpSt === 'off' ? 'Uit' : '-';
    const statVal  = this._stateObj(this._config.status_sensor)?.state ?? color.name;

    const accentBg   = color.bg;
    const accentText = color.text;

    // -- CSS via textContent (nooit HTML-geparsed) ----------------------
    let styleEl = this.shadowRoot.querySelector('style');
    if (!styleEl) {
      styleEl = document.createElement('style');
      this.shadowRoot.appendChild(styleEl);
    }
    styleEl.textContent = `
      :host { display: block; height: 100%; }

      ha-card {
        overflow: hidden;
        border-radius: 16px;
        font-family: var(--primary-font-family, 'Roboto', sans-serif);
        background: var(--ha-card-background, var(--card-background-color, #fff));
        box-shadow: var(--ha-card-box-shadow, none);
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      /* -- header strip -- */
      .header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 16px 10px;
        background: ${accentBg};
        color: ${accentText};
        transition: background 0.4s;
      }
      .header ha-icon {
        --mdc-icon-size: 28px;
        flex-shrink: 0;
      }
      .header-text { flex: 1; min-width: 0; }
      .header-title {
        font-size: 1rem;
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .header-status {
        font-size: 0.75rem;
        opacity: 0.88;
        margin-top: 1px;
      }

      /* -- storing banner -- */
      .fault-banner {
        display: ${isFault ? 'flex' : 'none'};
        align-items: center;
        gap: 8px;
        background: #B71C1C;
        color: #fff;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 8px 16px;
      }
      .fault-banner ha-icon { --mdc-icon-size: 18px; flex-shrink: 0; }
      .fault-banner .fault-msg {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      /* -- body -- */
      .body { padding: 14px 16px; flex: 1; }

      /* -- temp section -- */
      .temp-section {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        gap: 8px;
      }
      .temp-group {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
      }
      .temp-label {
        font-size: 0.68rem;
        color: var(--secondary-text-color, #888);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
      }
      .temp-big {
        font-size: 2.2rem;
        font-weight: 300;
        color: var(--primary-text-color, #212121);
        line-height: 1;
      }
      .temp-unit {
        font-size: 1rem;
        color: var(--secondary-text-color, #888);
      }

      /* target temp controls */
      .temp-control {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        gap: 4px;
      }
      .temp-setpoint {
        font-size: 1.9rem;
        font-weight: 500;
        color: ${accentBg};
        line-height: 1;
      }
      .temp-btns {
        display: flex;
        gap: 6px;
        margin-top: 4px;
      }
      .temp-btn {
        background: none;
        border: 1.5px solid ${accentBg};
        color: ${accentBg};
        border-radius: 50%;
        width: 32px;
        height: 32px;
        font-size: 1.2rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.15s, color 0.15s, transform 0.1s, opacity 0.1s;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
      }
      .temp-btn:hover {
        background: ${accentBg};
        color: ${accentText};
      }
      .temp-btn:active {
        background: ${accentBg};
        color: ${accentText};
        transform: scale(0.88);
        opacity: 0.75;
      }

      /* divider */
      .divider {
        height: 1px;
        background: var(--divider-color, #e0e0e0);
        margin: 4px 0 12px;
      }

      /* -- on/off buttons -- */
      .onoff-row {
        display: flex;
        gap: 8px;
        margin-bottom: 14px;
      }
      .onoff-btn {
        flex: 1;
        border: none;
        border-radius: 10px;
        padding: 9px 0;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        transition: background 0.2s, color 0.2s, opacity 0.2s, transform 0.1s;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
        letter-spacing: 0.03em;
      }
      .onoff-btn ha-icon { --mdc-icon-size: 18px; }
      .onoff-btn:active { transform: scale(0.95); opacity: 0.75; }

      .btn-on {
        background: ${isOn ? accentBg : 'var(--secondary-background-color, #f5f5f5)'};
        color:      ${isOn ? accentText : 'var(--secondary-text-color, #888)'};
      }
      .btn-off {
        background: ${!isOn ? '#546E7A' : 'var(--secondary-background-color, #f5f5f5)'};
        color:      ${!isOn ? '#fff'     : 'var(--secondary-text-color, #888)'};
      }

      /* -- sensor grid -- */
      .sensor-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      .sensor-tile {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 10px;
        padding: 8px 10px;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .sensor-name {
        font-size: 0.66rem;
        color: var(--secondary-text-color, #888);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .sensor-val {
        font-size: 1.15rem;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }
      .sensor-unit {
        font-size: 0.72rem;
        color: var(--secondary-text-color, #888);
      }
    `;

    // -- HTML via persistent ha-card element --------------------------
    let card = this.shadowRoot.querySelector('ha-card');
    if (!card) {
      card = document.createElement('ha-card');
      this.shadowRoot.appendChild(card);
      card.addEventListener('click', e => {
        const el = e.target.closest('[id]');
        if (!el) return;
        if      (el.id === 'btn-plus')  this._adjustTemp(+1);
        else if (el.id === 'btn-minus') this._adjustTemp(-1);
        else if (el.id === 'btn-on')    this._turnOn();
        else if (el.id === 'btn-off')   this._turnOff();
      });
    }

    card.innerHTML = `
      <!-- header -->
      <div class="header">
        <ha-icon icon="${isOn ? 'mdi:fire' : 'mdi:fire-off'}"></ha-icon>
        <div class="header-text">
          <div class="header-title">${this._config.title}</div>
          <div class="header-status">${statVal}</div>
        </div>
      </div>

      <!-- storing banner -->
      <div class="fault-banner">
        <ha-icon icon="mdi:alert-circle"></ha-icon>
        <span class="fault-msg">${bannerMsg}</span>
      </div>

      <div class="body">

        <!-- temperaturen -->
        <div class="temp-section">
          <div class="temp-group">
            <div class="temp-label">Ketelwater</div>
            <div>
              <span class="temp-big">${actual}</span>
              <span class="temp-unit">&deg;C</span>
            </div>
          </div>

          <div class="temp-control">
            <div class="temp-label">Instelling</div>
            <div class="temp-setpoint">${target}<span class="temp-unit" style="font-size:1rem">&deg;C</span></div>
            <div class="temp-btns">
              <button class="temp-btn" id="btn-minus">&#x2212;</button>
              <button class="temp-btn" id="btn-plus">+</button>
            </div>
          </div>
        </div>

        <div class="divider"></div>

        <!-- aan / uit -->
        <div class="onoff-row">
          <button class="onoff-btn btn-on" id="btn-on">
            <ha-icon icon="mdi:power"></ha-icon> Aan
          </button>
          <button class="onoff-btn btn-off" id="btn-off">
            <ha-icon icon="mdi:power-off"></ha-icon> Uit
          </button>
        </div>

        <!-- sensoren -->
        <div class="sensor-grid">
          <div class="sensor-tile">
            <div class="sensor-name">Schoorsteen</div>
            <div class="sensor-val">${flueVal} <span class="sensor-unit">${flueUnit}</span></div>
          </div>
          <div class="sensor-tile">
            <div class="sensor-name">Vermogen</div>
            <div class="sensor-val">${powVal} <span class="sensor-unit">${powUnit}</span></div>
          </div>
          <div class="sensor-tile">
            <div class="sensor-name">CV-pomp</div>
            <div class="sensor-val">${chPumpVal}</div>
          </div>
          <div class="sensor-tile">
            <div class="sensor-name">WW-pomp</div>
            <div class="sensor-val">${dhwPumpVal}</div>
          </div>
          <div class="sensor-tile" style="grid-column: 1 / -1;">
            <div class="sensor-name">Status</div>
            <div class="sensor-val" style="font-size:0.9rem; color:${accentBg}">${statVal}</div>
          </div>
        </div>

      </div>
    `;
  }

  getCardSize() { return 7; }

  static getConfigElement() { return null; }

  static getStubConfig() {
    return {
      type           : 'custom:naturela-pellet-card',
      title          : 'Pelletkachel',
      climate_entity : 'climate.schuurkachel',
      status_sensor  : 'sensor.schuurkachel_status',
      boiler_sensor  : 'sensor.schuurkachel_keteltemperatuur',
      flue_sensor    : 'sensor.schuurkachel_rookgastemperatuur',
      power_sensor   : 'sensor.schuurkachel_vermogen',
      ch_pump_sensor : 'binary_sensor.schuurkachel_cv_pomp',
      dhw_pump_sensor: 'binary_sensor.schuurkachel_warmwaterpomp',
      alarm_sensor   : '',
    };
  }
}

customElements.define('naturela-pellet-card', NaturelaPelletCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type        : 'naturela-pellet-card',
  name        : 'Naturela Pellet Stove Card',
  description : 'All-in-one kaart voor de Naturela BurnerTouch pelletkachel',
  preview     : false,
});
