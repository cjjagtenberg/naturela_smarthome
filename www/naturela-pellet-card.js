const STATUS_COLORS = {
  0:   { bg: '#546E7A', text: '#fff', name: 'Stand-by' },
  1:   { bg: '#FFA000', text: '#fff', name: 'Cleaning' },
  2:   { bg: '#E64A19', text: '#fff', name: 'Burning' },
  3:   { bg: '#FF6D00', text: '#fff', name: 'Cleaning' },
  4:   { bg: '#D32F2F', text: '#fff', name: 'Fault' },
  5:   { bg: '#1565C0', text: '#fff', name: 'Suspend' },
  6:   { bg: '#00897B', text: '#fff', name: 'Cleaning' },
  7:   { bg: '#6D4C41', text: '#fff', name: 'Cooling' },
  8:   { bg: '#E64A19', text: '#fff', name: 'Burning' },
  128: { bg: '#546E7A', text: '#fff', name: 'Stand-by' },
};

const HEADER_COLOR = '#1976D2';

function getStatusInfo(raw) {
  const num = parseInt(raw, 10);
  if (!isNaN(num) && STATUS_COLORS[num]) return STATUS_COLORS[num];

  const s = (raw || '').toLowerCase();
  if (s.includes('stand') || s === 'stand-by')
    return STATUS_COLORS[0];
  if (s.includes('fault') || s.includes('error') || s.includes('alarm'))
    return { bg: STATUS_COLORS[4].bg, text: STATUS_COLORS[4].text, name: raw };
  if (s.includes('ignit') || s.includes('firing') || s.includes('clean'))
    return STATUS_COLORS[1];
  // power1..power5 → show the power level
  const powerMatch = raw.match(/^[Pp]ower\s*(\d+)$/);
  if (powerMatch)
    return { bg: STATUS_COLORS[2].bg, text: STATUS_COLORS[2].text, name: 'Power ' + powerMatch[1] };
  if (s.includes('burn') || s.includes('power') || s.includes('keeping'))
    return STATUS_COLORS[2];
  if (s.includes('suspend') || s.includes('wait'))
    return STATUS_COLORS[5];
  if (s.includes('cool'))
    return STATUS_COLORS[7];
  return { bg: HEADER_COLOR, text: '#fff', name: raw || 'Unknown' };
}

class NaturelaPelletCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Do NOT clear _pendingTemp here — HA polls stale device data and would
    // reset the baseline mid-session. Timeout in _adjustTemp handles cleanup.
    this._render();
  }

  _s(id) {
    if (!id || !this._hass) return null;
    return this._hass.states[id] || null;
  }

  _adjustTemp(delta) {
    if (!this._hass || !this._config.climate_entity) return;
    const climate = this._s(this._config.climate_entity);
    if (!climate) return;
    const min  = climate.attributes.min_temp || 5;
    const max  = climate.attributes.max_temp || 90;
    const step = climate.attributes.target_temp_step || 1;

    // Use pending temp as baseline so rapid clicks stack correctly.
    // Never use HA state here — it may reflect a stale poll, not the last press.
    const haTemp  = parseFloat(climate.attributes.temperature) || 0;
    const current = this._pendingTemp !== undefined ? this._pendingTemp : haTemp;
    const newTemp = Math.min(max, Math.max(min, current + delta * step));
    if (newTemp === current) return;

    this._pendingTemp = newTemp;
    // Reset 8-second idle timer — clears _pendingTemp after user stops pressing
    if (this._pendingTimer) clearTimeout(this._pendingTimer);
    this._pendingTimer = setTimeout(() => {
      this._pendingTemp  = undefined;
      this._pendingTimer = undefined;
      this._render();
    }, 8000);

    this._hass.callService('climate', 'set_temperature', {
      entity_id: this._config.climate_entity,
      temperature: newTemp,
    });
    this._render(); // update display immediately, don't wait for HA push
  }

  _render() {
    if (!this._config || !this._hass || !this.shadowRoot) return;

    const cfg      = this._config;
    const climate  = this._s(cfg.climate_entity);
    const statusS  = this._s(cfg.status_sensor);
    const boilerS  = this._s(cfg.boiler_sensor);
    const flueS    = this._s(cfg.flue_sensor);
    const powerS   = this._s(cfg.power_sensor);
    const pumpS    = this._s(cfg.pump_sensor);
    const alarmS   = this._s(cfg.alarm_sensor);

    const alarmVal  = alarmS?.state ?? null;
    const hasAlarm  = alarmVal !== null
      && alarmVal !== 'unavailable'
      && alarmVal !== 'unknown'
      && alarmVal !== 'none'
      && alarmVal !== ''
      && alarmVal !== '0'
      && alarmVal !== 'off'
      && alarmVal !== 'OK'
      && alarmVal !== 'ok'
      && alarmVal !== 'normal'
      && alarmVal !== 'Normal'
      && alarmVal !== 'geen';

    const isOn    = climate?.state === 'heat';
    const targetT = this._pendingTemp !== undefined
      ? this._pendingTemp
      : (climate?.attributes?.temperature ?? '—');
    const boilerT = boilerS ? parseFloat(boilerS.state).toFixed(1) : '—';
    const flueT   = flueS   ? Math.round(parseFloat(flueS.state))  : '—';

    const statusRaw = statusS?.state ?? 'Unknown';

    // Derive power label from status when no power_sensor configured
    const powerFromStatus = (() => {
      const pm = statusRaw.match(/^[Pp]ower\s*(\d+)$/);
      if (pm) return 'P' + pm[1];
      if ((statusRaw || '').toLowerCase() === 'ps') return 'PS';
      return null;
    })();
    const powerVal = powerFromStatus ?? (powerS?.state ?? '-');

    const pumpOn    = pumpS ? pumpS.state === 'on' : (climate?.attributes?.ch_pump === true);
    const pumpLabel = pumpOn ? 'Active' : 'Inactive';

    const si       = getStatusInfo(statusRaw);
    const statusName = si.name;
    const headerBg   = isOn ? (si.bg || HEADER_COLOR) : HEADER_COLOR;
    const title      = cfg.title || 'Pellet Stove';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .card {
          background: var(--card-background-color, #ffffff);
          border-radius: 12px;
          overflow: hidden;
          font-family: var(--primary-font-family, Roboto, sans-serif);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.15));
        }
        .header {
          background: ${headerBg};
          color: #fff;
          padding: 14px 16px 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .header-icon  { font-size: 1.4em; line-height: 1; }
        .header-texts { flex: 1; }
        .header-title { font-size: 1.05em; font-weight: 600; line-height: 1.2; color: #fff; }
        .header-sub   { font-size: 0.8em; opacity: 0.85; margin-top: 1px; }
        .temps-row {
          display: flex;
          padding: 16px 16px 12px;
          gap: 8px;
        }
        .temp-block  { flex: 1; }
        .temp-label  {
          font-size: 0.68em; font-weight: 600; letter-spacing: 0.06em;
          color: var(--secondary-text-color, #9e9e9e); text-transform: uppercase; margin-bottom: 4px;
        }
        .temp-value  { font-size: 2em; font-weight: 300; color: var(--primary-text-color, #212121); line-height: 1.1; }
        .temp-unit   { font-size: 0.5em; vertical-align: super; font-weight: 400; }
        .target-block { flex: 1; text-align: right; }
        .target-value { font-size: 2em; font-weight: 700; color: ${HEADER_COLOR}; line-height: 1.1; }
        .target-controls { display: flex; gap: 8px; justify-content: flex-end; margin-top: 6px; }
        .ctrl-btn {
          width: 32px; height: 32px; border-radius: 50%;
          border: 2px solid #bdbdbd; background: transparent; cursor: pointer;
          font-size: 1.2em; color: #757575;
          display: flex; align-items: center; justify-content: center;
          line-height: 1; user-select: none;
        }
        .ctrl-btn:hover  { border-color: ${HEADER_COLOR}; color: ${HEADER_COLOR}; }
        .ctrl-btn:active { background: #f0f0f0; }
        .divider { height: 1px; background: var(--divider-color, #e0e0e0); margin: 0 16px; }
        .action-row { display: flex; padding: 12px 16px; gap: 10px; }
        .action-btn {
          flex: 1; padding: 10px 0;
          border: none; border-radius: 8px;
          font-size: 0.9em; font-weight: 600; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          gap: 6px; letter-spacing: 0.2px;
          transition: opacity 0.15s;
        }
        .action-btn:active { opacity: 0.8; }
        .btn-on  {
          background: ${isOn ? HEADER_COLOR : 'var(--secondary-background-color, #e0e0e0)'};
          color:      ${isOn ? '#fff'        : 'var(--secondary-text-color, #757575)'};
        }
        .btn-off {
          background: ${!isOn ? 'var(--secondary-background-color, #e0e0e0)' : 'var(--secondary-background-color, #f5f5f5)'};
          color:      ${!isOn ? 'var(--primary-text-color, #424242)'          : 'var(--secondary-text-color, #9e9e9e)'};
        }
        .info-grid {
          display: grid; grid-template-columns: 1fr 1fr;
          gap: 8px; padding: 0 16px 12px;
        }
        .info-tile {
          background: var(--secondary-background-color, #f5f5f5);
          border-radius: 8px; padding: 10px 12px;
        }
        .info-tile-label {
          font-size: 0.65em; font-weight: 600; letter-spacing: 0.06em;
          color: var(--secondary-text-color, #9e9e9e); text-transform: uppercase; margin-bottom: 4px;
        }
        .info-tile-value { font-size: 1.05em; font-weight: 500; color: var(--primary-text-color, #212121); }
        .info-tile.pump-active .info-tile-value { color: #388e3c; }
        .info-tile.full-width { grid-column: 1 / -1; }
        .alarm-banner {
          display: flex; align-items: center; gap: 8px;
          background: #D32F2F; color: #fff;
          padding: 9px 16px; font-size: 0.88em; font-weight: 600;
        }
        .alarm-banner-icon  { font-size: 1.1em; line-height: 1; }
        .alarm-banner-text  { flex: 1; }
        .alarm-banner-label {
          font-size: 0.75em; font-weight: 700; letter-spacing: 0.07em;
          text-transform: uppercase; opacity: 0.85;
        }
        .status-footer { border-top: 1px solid var(--divider-color, #e0e0e0); padding: 10px 16px 12px; }
        .status-footer-label {
          font-size: 0.65em; font-weight: 600; letter-spacing: 0.06em;
          color: var(--secondary-text-color, #9e9e9e); text-transform: uppercase; margin-bottom: 3px;
        }
        .status-footer-value { font-size: 1em; font-weight: 500; color: ${si.bg}; }
      </style>
      <div class="card">
        <div class="header">
          <div class="header-icon">🔥</div>
          <div class="header-texts">
            <div class="header-title">${title}</div>
            <div class="header-sub">${statusRaw}</div>
          </div>
        </div>
        ${hasAlarm ? `<div class="alarm-banner"><div class="alarm-banner-icon">⚠️</div><div class="alarm-banner-text"><div class="alarm-banner-label">Alarm / Fault</div><div>${alarmVal}</div></div></div>` : ''}
        <div class="temps-row">
          <div class="temp-block">
            <div class="temp-label">Boiler</div>
            <div class="temp-value">${boilerT}<span class="temp-unit">&deg;C</span></div>
          </div>
          <div class="target-block">
            <div class="temp-label" style="text-align:right">Target</div>
            <div class="target-value">${targetT}<span class="temp-unit" style="color:${HEADER_COLOR}">&deg;C</span></div>
            <div class="target-controls">
              <button class="ctrl-btn" id="tempDown">&#8722;</button>
              <button class="ctrl-btn" id="tempUp">&#43;</button>
            </div>
          </div>
        </div>
        <div class="divider"></div>
        <div class="action-row">
          <button class="action-btn btn-on"  id="btnOn">&#9210; On</button>
          <button class="action-btn btn-off" id="btnOff">&#9711; Off</button>
        </div>
        <div class="info-grid">
          <div class="info-tile">
            <div class="info-tile-label">Flue</div>
            <div class="info-tile-value">${flueT > 0 ? flueT + ' °C' : (flueT === 0 ? '0 °C' : flueT)}</div>
          </div>
          <div class="info-tile">
            <div class="info-tile-label">Power</div>
            <div class="info-tile-value">${powerVal !== '-' && powerVal !== 'unknown' && powerVal !== 'unavailable' ? powerVal : '-'}</div>
          </div>
          <div class="info-tile full-width ${pumpOn ? 'pump-active' : ''}">
            <div class="info-tile-label">Pump</div>
            <div class="info-tile-value">${pumpLabel}</div>
          </div>
        </div>
        <div class="status-footer">
          <div class="status-footer-label">Status</div>
          <div class="status-footer-value">${statusName}</div>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById('btnOn').addEventListener('click', () => {
      if (!this._hass || !this._config.climate_entity) return;
      this._hass.callService('climate', 'set_hvac_mode', {
        entity_id: this._config.climate_entity,
        hvac_mode: 'heat',
      });
    });
    this.shadowRoot.getElementById('btnOff').addEventListener('click', () => {
      if (!this._hass || !this._config.climate_entity) return;
      this._hass.callService('climate', 'set_hvac_mode', {
        entity_id: this._config.climate_entity,
        hvac_mode: 'off',
      });
    });
    this.shadowRoot.getElementById('tempDown').addEventListener('click', () => this._adjustTemp(-1));
    this.shadowRoot.getElementById('tempUp').addEventListener('click',   () => this._adjustTemp(1));
  }

  getCardSize() { return 7; }

  static getStubConfig() {
    return {
      climate_entity: 'climate.pellet_stove',
      status_sensor:  'sensor.pellet_stove_status',
      boiler_sensor:  'sensor.pellet_stove_boiler_temperature',
      flue_sensor:    'sensor.pellet_stove_flue_gas_temperature',
      alarm_sensor:   'sensor.pellet_stove_alarm',
    };
  }
}

customElements.define('naturela-pellet-card', NaturelaPelletCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type:        'naturela-pellet-card',
  name:        'Naturela Pellet Stove Card',
  description: 'Card for the Naturela BurnerTouch pellet stove',
  preview:     true,
});
