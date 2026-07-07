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
    // 兼容本地开发 (frontend/) 和 GitHub Pages (root)
    const paths = [];
    const isLocal = window.location.pathname.includes('/frontend/');
    if (isLocal) {
      paths.push('../data/product/product_data.json');
    }
    paths.push('data/product/product_data.json');

    for (const path of paths) {
      try {
        const resp = await fetch(path);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this._data = await resp.json();
        return this._data;
      } catch (e) {
        console.warn(path + ' 加载失败', e);
      }
    }

    this._loadPromise = null;
    throw new Error('HTTP 404');
  },

  /** 异步加载技能索引 */
  async loadSkillIndex() {
    try {
      const resp = await fetch('data/skill_index.json');
      if (resp.ok) return await resp.json();
    } catch (_) { /* ignore */ }
    return null;
  },

  get pets() {
    const pets = this._data?.pets || [];
    // GitHub Pages 上图片从 CDN 加载（jsDelivr）
    const isPages = window.location.hostname.includes('github.io');
    if (isPages) {
      pets.forEach(p => {
        if (p.image && !p.image.startsWith('http')) {
          let path = p.image.replace(/^\//, '');
          // 尝试WebP（浏览器支持时自动使用）
          const webpPath = path.replace(/\.png$/i, '.webp');
          // 用WebP，如果404会自动降级（由CDN处理）
          p.image = 'https://cdn.jsdelivr.net/gh/shan0thunder/roco-pvp@main/' + webpPath + '?v=2';
        }
      });
    }
    return pets;
  },
  get skills() { return this._data?.skills || []; },
  get teams() { return this._data?.pvp_teams || []; },
  get typeChart() { return this._data?.type_chart || {}; },
  get elements() { return this._data?.type_elements || []; },
  get petIndex() { return this._data?.index?.teams_by_pet || {}; },
  get meta() { return this._data?._meta || {}; },
  get risingPets() { return this._data?.rising_pets || []; },
};

// ============================================================
// Supabase 客户端
// ============================================================
const SupabaseDB = (() => {
  const supabaseUrl = 'https://nxphzmikyatvtebazspt.supabase.co';
  const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im54cGh6bWlreWF0dnRlYmF6c3B0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwNjE3MzksImV4cCI6MjA5ODYzNzczOX0.Uep50Y0KklvUKJ8q3OpnGKgYhhC8RlWhokg463EJLoY';
  let client = null;

  function getClient() {
    if (!client && typeof supabase !== 'undefined') {
      client = supabase.createClient(supabaseUrl, supabaseKey);
    }
    return client;
  }

  /** 获取所有分享阵容 */
  async function getTeams(sortBy = 'created_at', ascending = false) {
    const c = getClient();
    if (!c) return [];
    const { data } = await c.from('shared_teams')
      .select('*')
      .order(sortBy, { ascending })
      .limit(100);
    return data || [];
  }

  /** 发布阵容 */
  async function publishTeam(entry) {
    const c = getClient();
    if (!c) return null;
    const { data } = await c.from('shared_teams').insert(entry).select();
    return data?.[0] || null;
  }

  /** 点击计数 */
  async function clickTeam(id) {
    const c = getClient();
    if (!c) return;
    const { data: current } = await c.from('shared_teams').select('click_count').eq('id', id).single();
    const newCount = (current?.click_count || 0) + 1;
    await c.from('shared_teams').update({ click_count: newCount }).eq('id', id);
  }

  /** 按精灵名搜索 */
  async function searchTeams(keyword) {
    const c = getClient();
    if (!c) return [];
    const { data } = await c.from('shared_teams')
      .select('*')
      .contains('pet_names', [keyword])
      .limit(100);
    return data || [];
  }

  return { getTeams, publishTeam, clickTeam, searchTeams };
})();

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
