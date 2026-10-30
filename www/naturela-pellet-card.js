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
  // v38: status sensor delivers the literal Naturela BurnStatus labels.
  // Colour by phase; the shown name is always the label as-is.
  const s = String(raw || '').toLowerCase();
  const C = i => ({ bg: STATUS_COLORS[i].bg, text: STATUS_COLORS[i].text, name: raw || 'Unknown' });
  if (s.includes('stand')) return C(0);
  if (s.includes('fault') || s.includes('error') || s.includes('alarm') || s.includes('fail')
      || s.includes('no pellets') || s.includes('overheat')) return C(4);
  if (s === 'stopfiring') return C(7);
  if (s.startsWith('clearing') || s === 'charging' || s === 'firing') return C(1);
  if (s === 'keeping') return C(5);
  if (s === 'burning' || /^power\s*\d+$/.test(s)) return C(2);
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

    const haTemp  = parseFloat(climate.attributes.temperature) || 0;
    const current = this._pendingTemp !== undefined ? this._pendingTemp : haTemp;
    const newTemp = Math.min(max, Math.max(min, current + delta * step));
    if (newTemp === current) return;

    this._pendingTemp = newTemp;
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
    this._render();
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
    // v33: headerBg and headerText now use theme variables when stove is off
    const headerBg   = isOn ? (si.bg || HEADER_COLOR) : 'var(--secondary-background-color, #37474F)';
    const headerText = isOn ? '#fff' : 'var(--primary-text-color, #e0e0e0)';
    const title      = cfg.title || 'Pellet Stove';
    const tm         = this._timerModel(climate);

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
          color: ${headerText};
          padding: 14px 16px 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .header-icon  { font-size: 1.4em; line-height: 1; }
        .header-texts { flex: 1; }
        .header-title { font-size: 1.05em; font-weight: 600; line-height: 1.2; color: ${headerText}; }
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
        .timer-head {
          display: flex; align-items: center; gap: 8px; width: 100%;
          border: none; background: transparent; cursor: pointer;
          padding: 10px 16px; font: inherit; text-align: left;
          border-top: 1px solid var(--divider-color, #e0e0e0);
          color: var(--primary-text-color, #212121);
        }
        .timer-head-label { font-size: 0.65em; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--secondary-text-color, #9e9e9e); }
        .timer-head-sum { flex: 1; text-align: right; font-size: 0.85em; color: ${tm.planned ? HEADER_COLOR : 'var(--secondary-text-color, #9e9e9e)'}; font-weight: ${tm.planned ? 600 : 400}; }
        .timer-chev { font-size: 0.8em; color: var(--secondary-text-color, #9e9e9e); transition: transform .15s; }
        .timer-chev.open { transform: rotate(180deg); }
        .timer-body { padding: 0 16px 12px; display: flex; flex-direction: column; gap: 8px; }
        .timer-row { display: flex; align-items: center; gap: 8px; background: var(--secondary-background-color, #f5f5f5); border-radius: 8px; padding: 8px 12px; }
        .timer-row-label { flex: 1; font-size: 0.85em; color: var(--primary-text-color, #212121); }
        .timer-row-label small { display: block; font-size: 0.8em; color: var(--secondary-text-color, #9e9e9e); }
        .timer-val { min-width: 56px; text-align: center; font-weight: 600; color: var(--primary-text-color, #212121); }
        .timer-btns { display: flex; gap: 8px; }
        .timer-btns .action-btn { padding: 9px 0; }
        .btn-start { background: ${HEADER_COLOR}; color: #fff; }
        .btn-sec { background: var(--secondary-background-color, #e0e0e0); color: var(--primary-text-color, #424242); }
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
        ${tm.available ? this._timerHtml(tm) : ''}
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
    if (tm.available) this._bindTimer(tm);
  }

  // ---- v34: timer section ------------------------------------------------
  // Entities are found automatically on the same device as climate_entity
  // (naturela_smarthome >= 1.4.1), or set explicitly in the card config:
  // delay_entity, duration_entity, start_entity, off_after_entity,
  // cancel_entity, next_on_entity, next_off_entity.
  _timerEntity(cfgKey, translationKey, climate) {
    if (this._config[cfgKey]) return this._config[cfgKey];
    const reg = this._hass.entities || {};
    const dev = climate && reg[climate.entity_id] ? reg[climate.entity_id].device_id : null;
    if (!dev) return null;
    const hit = Object.values(reg).find(e => e.device_id === dev
      && e.platform === 'naturela_smarthome' && e.translation_key === translationKey);
    return hit ? hit.entity_id : null;
  }

  _timerModel(climate) {
    const id = {
      delay:    this._timerEntity('delay_entity', 'delay', climate),
      duration: this._timerEntity('duration_entity', 'burn_duration', climate),
      start:    this._timerEntity('start_entity', 'start_timer', climate),
      offAfter: this._timerEntity('off_after_entity', 'off_after_duration', climate),
      cancel:   this._timerEntity('cancel_entity', 'cancel_schedule', climate),
      nextOn:   this._timerEntity('next_on_entity', 'next_on', climate),
      nextOff:  this._timerEntity('next_off_entity', 'next_off', climate),
    };
    const ts = e => { const s = this._s(e); if (!s) return null; const d = new Date(s.state); return isNaN(d) ? null : d; };
    const num = e => { const s = this._s(e); const v = s ? parseFloat(s.state) : NaN; return isNaN(v) ? null : v; };
    const nextOn = ts(id.nextOn), nextOff = ts(id.nextOff);
    return {
      id,
      available: !!(id.delay && id.duration && id.start && id.cancel),
      delay: this._pendingDelay ?? num(id.delay),
      duration: this._pendingDuration ?? num(id.duration),
      nextOn, nextOff,
      planned: !!(nextOn || nextOff),
      isOn: climate?.state === 'heat',
    };
  }

  _t(key) {
    const nl = (this._hass?.language || '').startsWith('nl');
    const T = {
      timer:   ['Timer', 'Timer'],
      off:     ['Not active', 'Niet actief'],
      delay:   ['Delay', 'Voorlooptijd'],
      delayS:  ['turn on in', 'aan over'],
      dur:     ['Burn duration', 'Nalooptijd'],
      durS:    ['then off after', 'daarna uit na'],
      durOn:   ['turn off in', 'uit over'],
      offIn:   ['Turn off in', 'Uit over'],
      willOn:  ['Turns on at', 'Gaat aan om'],
      willOff: ['Turns off at', 'Gaat uit om'],
      cancelT: ['Cancel timer', 'Timer annuleren'],
      start:   ['Start timer', 'Start timer'],
      offAft:  ['Off after duration', 'Uit na nalooptijd'],
      cancel:  ['Cancel', 'Annuleren'],
      on:      ['On', 'Aan'],
      offW:    ['Off', 'Uit'],
      now:     ['now', 'nu'],
    };
    return (T[key] || [key, key])[nl ? 1 : 0];
  }

  _fmtTime(d) {
    if (!d) return '';
    const lang = this._hass?.language || undefined;
    const t = d.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' });
    const today = new Date();
    if (d.toDateString() === today.toDateString()) return t;
    return d.toLocaleDateString(lang, { weekday: 'short' }) + ' ' + t;
  }

  _fmtHours(h) {
    if (h === null || h === undefined) return '-';
    if (h === 0) return this._t('now');
    const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
    return mm ? `${hh}:${String(mm).padStart(2, '0')} u` : `${hh} u`;
  }

  _timerSummary(tm) {
    const parts = [];
    if (tm.nextOn)  parts.push(this._t('on') + ' ' + this._fmtTime(tm.nextOn));
    if (tm.nextOff) parts.push(this._t('offW') + ' ' + this._fmtTime(tm.nextOff));
    return parts.length ? parts.join(' · ') : this._t('off');
  }

  _timerHtml(tm) {
    const open = !!this._timerOpen;
    const planRow = (label, d) => d ? `<div class="timer-row">
          <div class="timer-row-label">${label}</div>
          <div class="timer-val">${this._fmtTime(d)}</div>
        </div>` : '';
    const plannedBody = `
      <div class="timer-body">
        ${planRow(this._t('willOn'), tm.nextOn)}
        ${planRow(this._t('willOff'), tm.nextOff)}
        <div class="timer-btns">
          <button class="action-btn btn-sec" id="tCancel">${this._t('cancelT')}</button>
        </div>
      </div>`;
    const setupBody = `
      <div class="timer-body">
        ${tm.isOn ? '' : `<div class="timer-row">
          <div class="timer-row-label">${this._t('delay')}<small>${this._t('delayS')}</small></div>
          <button class="ctrl-btn" id="tDelayDown">&#8722;</button>
          <div class="timer-val">${this._fmtHours(tm.delay)}</div>
          <button class="ctrl-btn" id="tDelayUp">&#43;</button>
        </div>`}
        <div class="timer-row">
          <div class="timer-row-label">${this._t('dur')}<small>${this._t(tm.isOn ? 'durOn' : 'durS')}</small></div>
          <button class="ctrl-btn" id="tDurDown">&#8722;</button>
          <div class="timer-val">${this._fmtHours(tm.duration)}</div>
          <button class="ctrl-btn" id="tDurUp">&#43;</button>
        </div>
        <div class="timer-btns">
          ${tm.isOn
            ? (tm.id.offAfter ? `<button class="action-btn btn-start" id="tOffAfter">&#9201; ${this._t('offIn')} ${this._fmtHours(tm.duration)}</button>` : '')
            : `<button class="action-btn btn-start" id="tStart">&#9201; ${this._t('start')}</button>`}
        </div>
      </div>`;
    const body = !open ? '' : (tm.planned ? plannedBody : setupBody);
    return `
      <button class="timer-head" id="tHead">
        <span>&#9201;</span>
        <span class="timer-head-label">${this._t('timer')}</span>
        <span class="timer-head-sum">${this._timerSummary(tm)}</span>
        <span class="timer-chev ${open ? 'open' : ''}">&#9660;</span>
      </button>${body}`;
  }

  _stepNumber(entityId, pendingKey, dir) {
    const s = this._s(entityId);
    if (!s) return;
    const a = s.attributes;
    const step = a.step || 0.5, min = a.min ?? 0, max = a.max ?? 24;
    const cur = this[pendingKey] ?? parseFloat(s.state);
    const next = Math.min(max, Math.max(min, Math.round((cur + dir * step) / step) * step));
    if (next === cur) return;
    this[pendingKey] = next;
    clearTimeout(this[pendingKey + 'T']);
    this[pendingKey + 'T'] = setTimeout(() => { this[pendingKey] = undefined; this._render(); }, 4000);
    this._hass.callService('number', 'set_value', { entity_id: entityId, value: next });
    this._render();
  }

  _bindTimer(tm) {
    const $ = id => this.shadowRoot.getElementById(id);
    const press = e => this._hass.callService('button', 'press', { entity_id: e });
    $('tHead').addEventListener('click', () => { this._timerOpen = !this._timerOpen; this._render(); });
    if (!this._timerOpen) return;
    if ($('tDelayDown')) $('tDelayDown').addEventListener('click', () => this._stepNumber(tm.id.delay, '_pendingDelay', -1));
    if ($('tDelayUp'))   $('tDelayUp').addEventListener('click',   () => this._stepNumber(tm.id.delay, '_pendingDelay', 1));
    if ($('tDurDown')) $('tDurDown').addEventListener('click', () => this._stepNumber(tm.id.duration, '_pendingDuration', -1));
    if ($('tDurUp'))   $('tDurUp').addEventListener('click',   () => this._stepNumber(tm.id.duration, '_pendingDuration', 1));
    if ($('tStart')) $('tStart').addEventListener('click', () => press(tm.id.start));
    if ($('tOffAfter')) $('tOffAfter').addEventListener('click', () => press(tm.id.offAfter));
    if ($('tCancel'))   $('tCancel').addEventListener('click',   () => press(tm.id.cancel));
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
