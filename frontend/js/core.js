/**
 * 洛克王国世界PVP助手 — 核心数据层
 * ======================================
 * 数据存储 + 工具函数 + 路由
 */

// ============================================================
// 数据层
// ============================================================
const DataStore = {
  _data: null,
  _loaded: false,
  _loadPromise: null,

  async load() {
    if (this._data) return this._data;
    if (this._loadPromise) return this._loadPromise;
    this._loadPromise = this._doLoad();
    return this._loadPromise;
  },
  async _doLoad() {
    try {
      const resp = await fetch('data/product/product_data.json');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this._data = await resp.json();
      return this._data;
    } catch (e) {
      console.warn('product_data.json 加载失败，尝试备用路径', e);
      try {
        const resp = await fetch('data/product/product_data.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this._data = await resp.json();
        return this._data;
      } catch (e2) {
        console.error('数据加载失败', e2);
        this._loadPromise = null;
        throw e2;
      }
    }
  },

  /** 异步加载技能索引 */
  async loadSkillIndex() {
    try {
      const resp = await fetch('data/skill_index.json');
      if (resp.ok) return await resp.json();
    } catch (_) { /* ignore */ }
    return null;
  },

  get pets() { return this._data?.pets || []; },
  get skills() { return this._data?.skills || []; },
  get teams() { return this._data?.pvp_teams || []; },
  get typeChart() { return this._data?.type_chart || {}; },
  get elements() { return this._data?.type_elements || []; },
  get petIndex() { return this._data?.index?.teams_by_pet || {}; },
  get meta() { return this._data?._meta || {}; },
  get risingPets() { return this._data?.rising_pets || []; },
};

// ============================================================
// 工具函数
// ============================================================
const Utils = {
  h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'className') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'innerHTML') el.innerHTML = v;
      else el.setAttribute(k, v);
    }
    for (const c of children) {
      if (c == null) continue;
      el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return el;
  },

  typeEmoji(mult) {
    if (mult >= 2) return '2x';
    if (mult <= 0) return '0x';
    if (mult < 1) return '0.5x';
    return '1x';
  },
  typeClass(mult) {
    if (mult >= 2) return 'type-cell-2';
    if (mult <= 0) return 'type-cell-0';
    if (mult < 1) return 'type-cell-05';
    return 'type-cell-1';
  },

  esc(str) { return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]); },

  sleep(ms) { return new Promise(r => setTimeout(r, ms)); },

  /** 截断文本 */
  truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
  },

  /** 根据技能属性返回颜色（BiliWiki 官方色值） */
  elementColor(elem) {
    const colors = {
      '普通':'#3F89B4',  /* rgba(63,137,180,0.8) */
      '草':'#4EBC73',    /* rgba(78,188,115,0.8) */
      '火':'#DB5525',    /* rgba(219,85,37,0.8)  */
      '水':'#6AA9FE',    /* rgba(106,169,254,0.8) */
      '光':'#4FC0FF',    /* rgba(79,192,255,0.8) */
      '地':'#9A7E3F',    /* rgba(154,126,63,0.8) */
      '冰':'#5FADDD',    /* rgba(95,173,221,0.8) */
      '龙':'#ED4962',    /* rgba(237,73,98,0.8) */
      '电':'#E7C506',    /* rgba(231,197,6,0.8) */
      '毒':'#BA62E0',    /* rgba(186,98,224,0.8) */
      '虫':'#94C11F',    /* rgba(148,193,31,0.8) */
      '武':'#FF9636',    /* rgba(255,150,54,0.8) */
      '翼':'#3EC7CA',    /* rgba(62,199,202,0.8) */
      '萌':'#FC7CAC',    /* rgba(252,124,172,0.8) */
      '幽':'#9446EC',    /* rgba(148,70,236,0.8) */
      '恶':'#CF467A',    /* rgba(207,70,122,0.8) */
      '机械':'#40CBA9',  /* rgba(64,203,169,0.8) */
      '幻':'#9198E2',    /* rgba(145,152,226,0.8) */
    };
    return colors[elem] || '#90a4ae';
  },
};

// ============================================================
// 路由
// ============================================================
const Router = {
  _currentRoute: '',
  _listeners: [],

  parse() {
    const hash = location.hash.slice(1) || 'pets';
    const parts = hash.split('/');
    return { route: parts[0], params: parts.slice(1) };
  },

  go(route, ...params) {
    location.hash = '#' + route + (params.length ? '/' + params.join('/') : '');
  },

  init() {
    window.addEventListener('hashchange', () => this._dispatch());
    this._dispatch();
  },

  _dispatch() {
    this._currentRoute = location.hash.slice(1) || 'pets';
    this._listeners.forEach(fn => fn(this.parse()));
  },

  onChange(fn) { this._listeners.push(fn); },
};
