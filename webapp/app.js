/* Movie Land Ultra — Glass Block WebApp Controller */
(() => {
  'use strict';

  // ==================== CRISP VECTOR SVG ICON SET (ZERO RAW EMOJIS) ====================
  const ICONS = {
    play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.5 4.8c0-1.1 1.2-1.8 2.2-1.2l11.2 7.2c.9.6.9 1.9 0 2.5L8.7 20.4c-1 .6-2.2-.1-2.2-1.2V4.8z"/></svg>',
    film: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="4" width="19" height="16" rx="3"/><path d="M7 4v16M17 4v16M2.5 9h4.5M17 9h4.5M2.5 15h4.5M17 15h4.5"/></svg>',
    tv: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="13" rx="3"/><path d="M8 21h8M12 18v3"/></svg>',
    home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 10.5 12 3.5l8.5 7v9a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5v-9z"/><path d="M9.5 21v-6.5h5V21"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7.2"/><path d="m20 20-3.8-3.8"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 4.8-9 4.8-9-4.8L12 3z"/><path d="m3 12.6 9 4.8 9-4.8"/><path d="m3 17.2 9 4.8 9-4.8"/></svg>',
    heart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20.4s-7.5-4.7-9.2-9C1.5 8 3.7 4.8 7.2 4.8c2 0 3.6 1 4.8 2.6 1.2-1.6 2.8-2.6 4.8-2.6 3.5 0 5.7 3.2 4.4 6.6-1.7 4.3-9.2 9-9.2 9z"/></svg>',
    heartFill: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 20.6s-7.6-4.7-9.3-9.1C1.4 8 3.6 4.7 7.2 4.7c2 0 3.6 1 4.8 2.6 1.2-1.6 2.8-2.6 4.8-2.6 3.6 0 5.8 3.3 4.5 6.8-1.7 4.4-9.3 9.1-9.3 9.1z"/></svg>',
    user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8.2" r="4"/><path d="M4.5 20c1.3-3.6 4.2-5.3 7.5-5.3s6.2 1.7 7.5 5.3"/></svg>',
    gift: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13M5 12v7.5A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V12"/><path d="M12 8H8.4a2.2 2.2 0 1 1 0-4.4C10.8 3.6 12 8 12 8zm0 0h3.6a2.2 2.2 0 1 0 0-4.4C13.2 3.6 12 8 12 8z"/></svg>',
    sparkles: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5 14.1 9l6.4 2.1-6.4 2.1L12 19.7l-2.1-6.5-6.4-2.1L9.9 9 12 2.5zm7.2 13.8.9 2.7 2.7.9-2.7.9-.9 2.7-.9-2.7-2.7-.9 2.7-.9.9-2.7zM4.8 2.8l.7 2.1 2.1.7-2.1.7-.7 2.1-.7-2.1L2 5.6l2.1-.7.7-2.1z"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2.8 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3L12 17.2l-5.6 3 1.1-6.3-4.6-4.5 6.3-.9L12 2.8z"/></svg>',
    eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.2 12S5.8 5.8 12 5.8 21.8 12 21.8 12 18.2 18.2 12 18.2 2.2 12 2.2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/></svg>',
    sliders: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 7h16M7 12h10M10 17h4"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.4 3.3 2.9 10.6c-.8.3-.8 1.4.1 1.7l4.7 1.6 1.8 5.6c.2.7 1.1.9 1.6.4l2.6-2.5 4.9 3.6c.6.4 1.5.1 1.7-.7l2.5-15.9c.1-.8-.6-1.4-1.4-1.1zM9.4 13.7l8.5-5.9-6.6 7.4-.5 2.6-1.4-4.1z"/></svg>',
    chevronRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M5 15H4.5A1.5 1.5 0 0 1 3 13.5v-9A1.5 1.5 0 0 1 4.5 3h9A1.5 1.5 0 0 1 15 4.5V5"/></svg>',
    share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7M16 6l-4-4-4 4M12 2v13"/></svg>',
    crown: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.5 18.5h17l1.5-10-5.2 3.8L12 5l-4.8 7.3L2 8.5l1.5 10z"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m8.5 12.3 2.3 2.3 4.8-5"/></svg>',
    wallet: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5.5" width="19" height="13.5" rx="3"/><path d="M16 12.2h5.5M5.5 5.5l11-2.5 1.5 2.5"/></svg>',
    users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8.5" r="3.5"/><path d="M2.5 19.5c1.1-3 3.4-4.5 6.5-4.5s5.4 1.5 6.5 4.5"/><circle cx="17" cy="9.5" r="2.5"/><path d="M18 14.8c1.8.5 3.1 1.7 3.8 3.7"/></svg>',
    flame: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12.7 2.3c.4 3.4-1.6 5.4-3.1 7.1-1.2 1.3-2.1 2.7-2.1 4.6a4.5 4.5 0 0 0 9 0c0-2-.9-3.7-2.2-5.1-.2 1.5-1.1 2.5-2.1 2.9.8-2.4 1.5-5.6.5-9.5z"/></svg>',
    compass: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polygon points="15.8 8.2 13.7 13.7 8.2 15.8 10.3 10.3 15.8 8.2" fill="currentColor" stroke="none"/></svg>',
    masks: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5c2.8-1 6.2-1 9 0v6.2c0 3.3-2 6-4.5 6.8C6 17.7 4 15 4 11.7V5.5z"/><path d="M11 8.5c2.8-1 6.2-1 9 0v5.2c0 3.1-2 5.6-4.5 6.3-1.5-.4-2.8-1.4-3.6-2.8"/></svg>',
    rocket: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 15.5c1.2-3.4 4.3-8.5 11.8-11.5 1 7.5-4.1 10.6-7.5 11.8L5 15.5z"/><path d="M9.5 15.5 8 19l-3-3 3.5-1.5M14.5 9.5h.01"/></svg>',
    wand: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="m4 20 11-11M13 7l4 4M15 3v2M21 9h-2M19.2 4.8l-1.4 1.4"/></svg>',
    bolt: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13.5 2.5 5 13.5h6.2L10.5 21.5 19 10.5h-6.2l.7-8z"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4.5 6.2V12c0 4.6 3.2 7.8 7.5 9 4.3-1.2 7.5-4.4 7.5-9V6.2L12 3z"/></svg>',
    smile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M8.5 14.5c1 1.5 2.2 2.2 3.5 2.2s2.5-.7 3.5-2.2"/><circle cx="9.2" cy="9.8" r="1" fill="currentColor"/><circle cx="14.8" cy="9.8" r="1" fill="currentColor"/></svg>',
    ghost: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 19.5v-8a7 7 0 0 1 14 0v8l-2.3-1.8-2.3 1.8-2.4-1.8-2.3 1.8-2.3-1.8L5 19.5z"/><circle cx="9.5" cy="11" r="1" fill="currentColor"/><circle cx="14.5" cy="11" r="1" fill="currentColor"/></svg>',
    landmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h18M4 19.5h16M6 10v9.5M10 10v9.5M14 10v9.5M18 10v9.5M12 3.5 3.5 8h17L12 3.5z"/></svg>',
    sword: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 4.5 9.5 14.5M14.5 4.5h5v5M7.5 12.5l4 4M4.5 19.5l3.5-3.5"/></svg>',
    trophy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h10v6a5 5 0 0 1-10 0V4zM7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3M12 15v4M8.5 19.5h7"/></svg>',
    music: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 17.5V6l11-2v11.5"/><circle cx="6.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="15.5" r="2.5"/></svg>',
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="9"/><path d="M3.5 12h17M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18"/></svg>',
    book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 4.5h6.5a3 3 0 0 1 3 3v12a2.5 2.5 0 0 0-2.5-2.5H4.5V4.5zM19.5 4.5H13a3 3 0 0 0-3 3v12a2.5 2.5 0 0 1 2.5-2.5h7V4.5z"/></svg>',
    arrowUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M6 11l6-6 6 6"/></svg>',
  };

  function ico(name) {
    return `<span class="icon">${ICONS[name] || ICONS.film}</span>`;
  }

  // Genre visual themes (ambient tinted glass + colored squircle icon)
  const GENRE_THEMES = {
    flame:    { bg: 'linear-gradient(135deg, #3c1c17 0%, #1c1414 100%)', sq: 'linear-gradient(145deg, #ff453a, #c81d25)', accent: '#ff6961' },
    compass:  { bg: 'linear-gradient(135deg, #12362a 0%, #111c19 100%)', sq: 'linear-gradient(145deg, #30d158, #1c8c3d)', accent: '#4cd964' },
    masks:    { bg: 'linear-gradient(135deg, #251d42 0%, #161421 100%)', sq: 'linear-gradient(145deg, #5e5ce6, #3e3cb8)', accent: '#8e8cf7' },
    rocket:   { bg: 'linear-gradient(135deg, #132c45 0%, #121822 100%)', sq: 'linear-gradient(145deg, #0a84ff, #005ecb)', accent: '#5ac8fa' },
    wand:     { bg: 'linear-gradient(135deg, #351946 0%, #191321 100%)', sq: 'linear-gradient(145deg, #bf5af2, #892ec2)', accent: '#d783ff' },
    bolt:     { bg: 'linear-gradient(135deg, #401725 0%, #1b1316 100%)', sq: 'linear-gradient(145deg, #ff375f, #be1840)', accent: '#ff6482' },
    shield:   { bg: 'linear-gradient(135deg, #1c243a 0%, #13151e 100%)', sq: 'linear-gradient(145deg, #64d2ff, #0a84ff)', accent: '#70d7ff' },
    smile:    { bg: 'linear-gradient(135deg, #3c2c12 0%, #1c1811 100%)', sq: 'linear-gradient(145deg, #ff9f0a, #d97706)', accent: '#ffb340' },
    users:    { bg: 'linear-gradient(135deg, #12333b 0%, #111b1e 100%)', sq: 'linear-gradient(145deg, #32ade6, #0a84ff)', accent: '#64d2ff' },
    heart:    { bg: 'linear-gradient(135deg, #42172f 0%, #1c1318 100%)', sq: 'linear-gradient(145deg, #ff2d55, #c61a3b)', accent: '#ff6482' },
    sparkles: { bg: 'linear-gradient(135deg, #3b2615 0%, #1b1612 100%)', sq: 'linear-gradient(145deg, #ff9f0a, #ff5e3a)', accent: '#ffb340' },
    ghost:    { bg: 'linear-gradient(135deg, #2b1a36 0%, #16131a 100%)', sq: 'linear-gradient(145deg, #ac8e68, #636366)', accent: '#d1c4e9' },
    landmark: { bg: 'linear-gradient(135deg, #33271a 0%, #191613 100%)', sq: 'linear-gradient(145deg, #d4a373, #9c6644)', accent: '#e6be8a' },
    search:   { bg: 'linear-gradient(135deg, #1b2838 0%, #13161d 100%)', sq: 'linear-gradient(145deg, #5ac8fa, #0a84ff)', accent: '#70d7ff' },
    default:  { bg: 'linear-gradient(135deg, #24242b 0%, #16161a 100%)', sq: 'linear-gradient(145deg, #636366, #3a3a3c)', accent: '#a1a1a6' },
  };

  // ==================== STATE ====================
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try { tg.ready(); tg.expand(); } catch (_) {}
  }

  const state = {
    view: 'home',
    movies: [],
    genres: [],
    trailers: [],
    config: {
      webapp_title: 'Movie Land',
      webapp_subtitle: "O'zbek tilidagi kinolar • 24/7",
      webapp_banner: '',
      vip_7_price: 10000,
      vip_30_price: 25000,
      vip_90_price: 60000,
      ref_reward_amount: 1500,
      daily_reward_amount: 1000,
      bot_username: 'movieeland_bot',
      channel_url: 'https://t.me/movieee_land',
      group_url: 'https://t.me/movieeland_group',
    },
    stats: { total_movies: 0, total_serials: 0, total_genres: 0 },
    user: null,
    favorites: new Set(JSON.parse(localStorage.getItem('ml_favs') || '[]')),
    activeGenre: 'all',
    searchQuery: '',
    filterType: 'all', // all | movie | serial
    sortMode: 'newest', // newest | popular | rating
    selectedVipDays: 30,
    activeMovie: null,
    chatHistory: [],
    theme: localStorage.getItem('ml_theme') || 'dark',
  };

  // ==================== HELPERS ====================
  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtNum(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function fmtViews(n) {
    const v = Number(n) || 0;
    if (v >= 1000000) return (v / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (v >= 1000) return (v / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(v);
  }

  // Client-side phonetic key so "garry poter" / "gerry poter" / "harry potter" matches "Garri Potter" immediately!
  function phoneticKey(s) {
    const cyr = {
      а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'yo',ж:'j',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',
      н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'x',ц:'s',ч:'ch',ш:'sh',щ:'sh',
      ъ:'',ы:'i',ь:'',э:'e',ю:'yu',я:'ya',ў:'o',қ:'q',ғ:'g',ҳ:'h'
    };
    let t = String(s || '').toLowerCase().replace(/[а-яёўқғҳ]/g, c => cyr[c] || c);
    t = t.replace(/[ʻ‘’`ʼ']/g, '').replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    const syn = {
      'harry potter': 'garri potter', 'garry poter': 'garri potter', 'gerry poter': 'garri potter',
      'garry potter': 'garri potter', 'gerry potter': 'garri potter', 'moon knight': 'oy ritsari',
      'spider man': 'orgimchak odam', 'spiderman': 'orgimchak odam', 'spaydermen': 'orgimchak odam',
      'merlin': 'afsungar merlin', 'bethoven': 'beethoven', 'betxoven': 'beethoven',
    };
    Object.keys(syn).forEach(k => { if (t.includes(k)) t = t.replace(k, syn[k]); });
    t = t.replace(/ph/g, 'f').replace(/oo/g, 'u').replace(/ee/g, 'i')
         .replace(/y/g, 'i').replace(/q/g, 'k').replace(/c/g, 'k').replace(/w/g, 'v').replace(/h/g, 'x')
         .replace(/([a-z])\1+/g, '$1');
    return t.replace(/\s+/g, ' ').trim();
  }

  function haptic(kind = 'light') {
    try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(kind); } catch (_) {}
  }

  let toastTimer = null;
  function showToast(msg) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  }

  function applyTheme(t) {
    state.theme = t === 'light' ? 'light' : 'dark';
    document.documentElement.classList.toggle('light', state.theme === 'light');
    localStorage.setItem('ml_theme', state.theme);
    const btn = document.getElementById('themeBtn');
    if (btn) btn.innerHTML = ico(state.theme === 'light' ? 'moon' : 'sun');
    const sw = document.getElementById('profileThemeSwitch');
    if (sw) sw.classList.toggle('on', state.theme === 'dark');
    if (tg && tg.setHeaderColor) {
      try {
        tg.setHeaderColor(state.theme === 'light' ? '#f2f2f7' : '#000000');
        tg.setBackgroundColor(state.theme === 'light' ? '#f2f2f7' : '#000000');
      } catch (_) {}
    }
  }

  function openBotLink(startParam) {
    const bot = state.config.bot_username || 'movieeland_bot';
    const url = startParam ? `https://t.me/${bot}?start=${encodeURIComponent(startParam)}` : `https://t.me/${bot}`;
    if (tg && tg.openTelegramLink) {
      tg.openTelegramLink(url);
    } else {
      window.open(url, '_blank');
    }
  }

  function openExternalUrl(url) {
    if (!url) return;
    if (url.startsWith('https://t.me/') && tg && tg.openTelegramLink) {
      tg.openTelegramLink(url);
    } else if (tg && tg.openLink) {
      tg.openLink(url);
    } else {
      window.open(url, '_blank');
    }
  }

  function watchMovieInBot(code, epNum = 1) {
    haptic('medium');
    openBotLink(`watch_${code}_${epNum}`);
  }

  // ==================== NAVIGATION ====================
  function setView(v) {
    state.view = v;
    document.querySelectorAll('.view').forEach(el => el.classList.toggle('active', el.id === `view-${v}`));
    document.querySelectorAll('[data-nav]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.nav === v);
    });
    if (v === 'search') {
      const inp = document.getElementById('searchPageInput');
      if (inp) { inp.value = state.searchQuery; setTimeout(() => inp.focus(), 60); }
      renderSearchView();
    } else if (v === 'genres') {
      renderGenresView();
    } else if (v === 'favorites') {
      renderFavoritesView();
    } else if (v === 'profile') {
      renderProfileView();
    } else {
      renderHomeGrid();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ==================== FILTERING & SORTING ====================
  function filterMovies(list, opts = {}) {
    const q = (opts.query !== undefined ? opts.query : state.searchQuery).trim();
    const g = opts.genre !== undefined ? opts.genre : state.activeGenre;
    const ft = opts.type !== undefined ? opts.type : state.filterType;
    const qLow = q.toLowerCase();
    const qPhon = phoneticKey(q);

    let out = list.filter(m => {
      if (ft === 'serial' && !m.is_serial) return false;
      if (ft === 'movie' && m.is_serial) return false;
      if (g && g !== 'all') {
        const mg = String(m.genre || '').toLowerCase();
        if (!mg.includes(g.toLowerCase())) return false;
      }
      if (q) {
        const codeStr = String(m.code || '');
        const nameLow = String(m.name || '').toLowerCase();
        const capLow = String(m.caption || '').toLowerCase();
        const genLow = String(m.genre || '').toLowerCase();
        const yrStr = String(m.year || '');
        const namePhon = phoneticKey(m.name);
        const hit =
          codeStr === qLow.replace(/^#/, '') ||
          nameLow.includes(qLow) ||
          genLow.includes(qLow) ||
          yrStr.includes(qLow) ||
          capLow.includes(qLow) ||
          (qPhon.length >= 3 && (namePhon.includes(qPhon) || qPhon.split(' ').every(w => w.length < 2 || namePhon.includes(w))));
        if (!hit) return false;
      }
      return true;
    });

    const sm = opts.sort || state.sortMode;
    if (sm === 'popular') {
      out = out.slice().sort((a, b) => (b.views || 0) - (a.views || 0));
    } else if (sm === 'rating') {
      out = out.slice().sort((a, b) => (parseFloat(b.imdb) || 0) - (parseFloat(a.imdb) || 0));
    }
    return out;
  }

  // ==================== RENDERERS ====================
  function movieCardHTML(m) {
    const isSer = Boolean(m.is_serial) || (Number(m.episodes_count) > 1);
    const eps = Math.max(1, Number(m.episodes_count) || 1);
    const leftPill = isSer
      ? `<span class="ep-pill">${ico('tv')}<span>${eps} qism</span></span>`
      : `<span class="hd-pill">HD</span>`;
    const poster = m.photo_id
      ? `<img class="poster-img" src="${esc(m.photo_id)}" alt="${esc(m.name)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
         <div class="poster-fallback" style="display:none">${ico('film')}<span>#${esc(m.code)}</span></div>`
      : `<div class="poster-fallback">${ico('film')}<span>#${esc(m.code)}</span></div>`;

    const primaryGenre = String(m.genre || 'Kino').split(',')[0].trim();

    return `
      <article class="movie-card" data-code="${esc(m.code)}">
        <div class="poster-frame">
          ${poster}
          <div class="poster-scrim"></div>
          <div class="poster-top">
            <span class="badge-glass rating tabular">${ico('star')}<span>${esc(m.imdb || '8.4')}</span></span>
            <span class="badge-glass tabular">${ico('eye')}<span>${fmtViews(m.views)}</span></span>
          </div>
          <div class="poster-bottom">
            ${leftPill}
            <span class="code-pill tabular">#${esc(m.code)}</span>
          </div>
        </div>
        <div class="movie-name">${esc(m.name)}</div>
        <div class="movie-meta">${esc(m.year || '2024')} • ${esc(primaryGenre)}</div>
      </article>
    `;
  }

  function bindCardClicks(root) {
    if (!root) return;
    root.querySelectorAll('.movie-card[data-code]').forEach(card => {
      card.addEventListener('click', () => {
        const m = state.movies.find(x => String(x.code) === String(card.dataset.code));
        if (m) openMovieDetail(m);
      });
    });
  }

  function renderGenrePills() {
    const rail = document.getElementById('genrePills');
    if (!rail) return;
    const pills = [
      `<button class="chip-pill ${state.activeGenre === 'all' ? 'active' : ''}" data-g="all">Barchasi</button>`,
      `<button class="chip-pill ${state.filterType === 'serial' ? 'active' : ''}" data-g="__serials">${ico('tv')}<span>Seriallar</span></button>`,
    ];
    state.genres.slice(0, 14).forEach(g => {
      const act = state.filterType === 'all' && state.activeGenre === g.name;
      pills.push(`<button class="chip-pill ${act ? 'active' : ''}" data-g="${esc(g.name)}">${esc(g.name)}</button>`);
    });
    rail.innerHTML = pills.join('');
    rail.querySelectorAll('[data-g]').forEach(btn => {
      btn.addEventListener('click', () => {
        haptic('light');
        const g = btn.dataset.g;
        if (g === '__serials') {
          state.filterType = state.filterType === 'serial' ? 'all' : 'serial';
          state.activeGenre = 'all';
        } else {
          state.filterType = 'all';
          state.activeGenre = g;
        }
        renderGenrePills();
        renderHomeGrid();
      });
    });
  }

  function renderTrailers() {
    const rail = document.getElementById('storiesRail');
    const sec = document.getElementById('trailersSection');
    if (!rail || !sec) return;
    const items = state.trailers.length > 0
      ? state.trailers.map(t => ({ title: t.title, img: t.poster_url, url: t.video_url, code: null }))
      : state.movies.slice(0, 10).map(m => ({ title: m.name, img: m.photo_id, url: '', code: m.code }));

    if (!items.length) { sec.style.display = 'none'; return; }
    sec.style.display = 'block';

    rail.innerHTML = items.map((it, idx) => `
      <div class="story-item" data-sidx="${idx}">
        <div class="story-ring">
          ${it.img ? `<img class="story-img" src="${esc(it.img)}" alt="${esc(it.title)}" loading="lazy">` : `<div class="story-img"></div>`}
          <span class="story-play">${ico('play')}</span>
        </div>
        <div class="story-name">${esc(it.title)}</div>
      </div>
    `).join('');

    rail.querySelectorAll('.story-item').forEach(el => {
      el.addEventListener('click', () => {
        const it = items[Number(el.dataset.sidx)];
        if (!it) return;
        if (it.url) {
          openExternalUrl(it.url);
        } else if (it.code) {
          const m = state.movies.find(x => String(x.code) === String(it.code));
          if (m) openMovieDetail(m);
        }
      });
    });
  }

  function renderHomeGrid() {
    const grid = document.getElementById('homeGrid');
    const titleEl = document.getElementById('homeGridTitle');
    if (!grid) return;

    const filtered = filterMovies(state.movies);
    if (titleEl) {
      if (state.searchQuery.trim()) {
        titleEl.textContent = `Qidiruv natijalari (${filtered.length})`;
      } else if (state.filterType === 'serial') {
        titleEl.textContent = `Seriallar (${filtered.length})`;
      } else if (state.activeGenre !== 'all') {
        titleEl.textContent = `${state.activeGenre} (${filtered.length})`;
      } else {
        titleEl.textContent = "Yangi qo'shilganlar";
      }
    }

    if (!filtered.length) {
      grid.innerHTML = `
        <div class="glass-block empty-block" style="grid-column:1/-1">
          <div class="empty-icon">${ico('search')}</div>
          <h3>Hech narsa topilmadi</h3>
          <p>Boshqa so'z bilan qidiring yoki Movie Land AI yordamchisidan so'rang.</p>
          <button class="primary-btn" id="emptyAiBtn">${ico('sparkles')}<span>Movie Land AI dan so'rash</span></button>
        </div>`;
      const btn = document.getElementById('emptyAiBtn');
      if (btn) btn.addEventListener('click', () => openAiModal(state.searchQuery));
      return;
    }

    grid.innerHTML = filtered.slice(0, 60).map(movieCardHTML).join('');
    bindCardClicks(grid);
  }

  function renderSearchView() {
    const grid = document.getElementById('searchGrid');
    const meta = document.getElementById('searchMeta');
    if (!grid) return;
    const filtered = filterMovies(state.movies, { genre: 'all', type: state.filterType });
    if (meta) {
      meta.textContent = state.searchQuery.trim()
        ? `«${state.searchQuery.trim()}» bo'yicha ${filtered.length} ta natija`
        : `Jami ${filtered.length} ta kino va serial`;
    }
    if (!filtered.length) {
      grid.innerHTML = `
        <div class="glass-block empty-block" style="grid-column:1/-1">
          <div class="empty-icon">${ico('search')}</div>
          <h3>Topilmadi</h3>
          <p>Bu kino bazada bo'lmasa bot orqali buyurtma bering yoki AI dan so'rang.</p>
          <button class="primary-btn" id="searchEmptyAi">${ico('sparkles')}<span>AI orqali qidirish</span></button>
        </div>`;
      const b = document.getElementById('searchEmptyAi');
      if (b) b.addEventListener('click', () => openAiModal(state.searchQuery));
      return;
    }
    grid.innerHTML = filtered.slice(0, 80).map(movieCardHTML).join('');
    bindCardClicks(grid);
  }

  function renderGenresView() {
    const grid = document.getElementById('genresGrid');
    const sub = document.getElementById('genresSubtitle');
    if (!grid) return;
    if (sub) sub.textContent = `${state.genres.length} ta janr • kayfiyatingizga mosini tanlang`;

    grid.innerHTML = state.genres.map((g, idx) => {
      const th = GENRE_THEMES[g.icon] || GENRE_THEMES.default;
      const featured = idx < 2 ? ' featured' : '';
      const fanHtml = (g.posters || []).slice(0, idx < 2 ? 4 : 3).map(url =>
        `<img class="fan-poster" src="${esc(url)}" alt="" loading="lazy">`
      ).join('');
      return `
        <div class="genre-card${featured}" data-genre="${esc(g.name)}" style="background:${th.bg}">
          <div class="genre-icon-sq" style="background:${th.sq}">${ico(g.icon || 'film')}</div>
          <div class="genre-info">
            <div class="genre-title">${esc(g.name)}</div>
            <div class="genre-count tabular" style="color:${th.accent}">
              <span>${g.count} ta kino</span>${ico('chevronRight')}
            </div>
          </div>
          <div class="genre-fan">${fanHtml}</div>
        </div>
      `;
    }).join('');

    grid.querySelectorAll('.genre-card[data-genre]').forEach(card => {
      card.addEventListener('click', () => {
        haptic('light');
        state.filterType = 'all';
        state.activeGenre = card.dataset.genre;
        state.searchQuery = '';
        const hi = document.getElementById('heroSearchInput');
        if (hi) hi.value = '';
        renderGenrePills();
        setView('home');
      });
    });
  }

  function renderFavoritesView() {
    const grid = document.getElementById('favGrid');
    if (!grid) return;
    const favMovies = state.movies.filter(m => state.favorites.has(String(m.code)));
    if (!favMovies.length) {
      grid.innerHTML = `
        <div class="glass-block empty-block" style="grid-column:1/-1">
          <div class="empty-icon">${ico('heart')}</div>
          <h3>Sevimlilar ro'yxati bo'sh</h3>
          <p>Yoqqan kino yoki serial kartasidagi yurakcha tugmasini bosib saqlab qo'ying.</p>
          <button class="primary-btn" id="favBrowseBtn">${ico('film')}<span>Katalogni ko'rish</span></button>
        </div>`;
      const b = document.getElementById('favBrowseBtn');
      if (b) b.addEventListener('click', () => setView('home'));
      return;
    }
    grid.innerHTML = favMovies.map(movieCardHTML).join('');
    bindCardClicks(grid);
  }

  function renderProfileView() {
    const host = document.getElementById('profileStack');
    if (!host) return;

    const u = state.user || {
      id: 0, full_name: 'Mehmon', username: '', photo_url: '',
      joined_at: '', balance: 0, ref_count: 0, is_premium: false, premium_until: '', vip_tag: 'PREMIUM'
    };
    const cfg = state.config;
    const initials = (u.full_name || 'M').trim().slice(0, 1).toUpperCase();
    const avatarInner = u.photo_url ? `<img src="${esc(u.photo_url)}" alt="">` : esc(initials);
    const uname = u.username ? `@${u.username}` : 'Telegram foydalanuvchi';
    const joined = u.joined_at ? `A'zo: ${String(u.joined_at).slice(0, 10)}` : 'Movie Land Ultra';
    const statusBadge = u.is_premium
      ? `<span class="status-pill vip">${ico('crown')}<span>VIP FAOL</span></span>`
      : `<span class="status-pill std">Standard</span>`;

    const plans = [
      { days: 7, label: '7 kun', price: cfg.vip_7_price },
      { days: 30, label: '30 kun', price: cfg.vip_30_price },
      { days: 90, label: '90 kun', price: cfg.vip_90_price },
    ];
    const activePlan = plans.find(p => p.days === state.selectedVipDays) || plans[1];
    const vipSubText = u.is_premium
      ? `Amal qilish muddati: ${String(u.premium_until || '').slice(0, 10)} gacha • [${u.vip_tag || 'PREMIUM'}]`
      : `${fmtNum(cfg.vip_7_price)} so'm dan boshlab`;

    const refLink = u.id
      ? `https://t.me/${cfg.bot_username}?start=ref_${u.id}`
      : `https://t.me/${cfg.bot_username}`;

    host.innerHTML = `
      <section class="glass-block profile-hero">
        <div class="avatar-circle">${avatarInner}</div>
        <div style="min-width:0;flex:1">
          <div class="profile-name-row">
            <div class="profile-name">${esc(u.full_name)}</div>
            ${statusBadge}
          </div>
          <div class="profile-sub">${esc(uname)} • ${esc(joined)}</div>
        </div>
      </section>

      <section class="metrics-grid">
        <div class="glass-block metric-card">
          <div class="metric-head">
            <span class="sq-icon sq-green">${ico('wallet')}</span>
            <span>Balans</span>
          </div>
          <div class="metric-val tabular">${fmtNum(u.balance)} so'm</div>
        </div>
        <div class="glass-block metric-card">
          <div class="metric-head">
            <span class="sq-icon sq-blue">${ico('users')}</span>
            <span>Takliflar</span>
          </div>
          <div class="metric-val tabular">${u.ref_count} ta do'st</div>
        </div>
      </section>

      <section class="glass-block vip-card">
        <div class="vip-head">
          <div class="vip-title-row">
            <span class="sq-icon sq-gold">${ico('crown')}</span>
            <div>
              <h2>Movie Land Premium</h2>
              <div class="inset-sub">${esc(vipSubText)}</div>
            </div>
          </div>
        </div>

        <div class="vip-perks">
          <div class="vip-perk">${ico('check')}<span>Majburiy kanallarga a'zo bo'lish shart emas</span></div>
          <div class="vip-perk">${ico('check')}<span>Reklamasiz tezkor yuklash va maxsus VIP teg</span></div>
          <div class="vip-perk">${ico('check')}<span>Kuniga 5 tagacha kino buyurtma qilish imkoniyati</span></div>
        </div>

        <div class="vip-plans">
          ${plans.map(p => `
            <button class="plan-tile ${p.days === state.selectedVipDays ? 'selected' : ''}" data-days="${p.days}">
              <div class="plan-dur">${p.label}</div>
              <div class="plan-price tabular">${fmtNum(p.price)}</div>
              <div class="plan-unit">so'm</div>
            </button>
          `).join('')}
        </div>

        <div class="vip-actions">
          <button class="primary-btn" id="buyVipBalanceBtn">
            ${ico('crown')}
            <span>${u.is_premium ? 'VIP muddatini uzaytirish' : 'Balansdan faollashtirish'} (${fmtNum(activePlan.price)} so'm)</span>
          </button>
          <button class="secondary-btn" id="buyVipCardBtn">
            ${ico('send')}
            <span>Botda karta orqali to'lash</span>
          </button>
        </div>
      </section>

      <section class="glass-block inset-group">
        <button class="inset-row" id="copyRefRow">
          <div class="inset-left">
            <span class="sq-icon sq-blue">${ico('copy')}</span>
            <div>
              <div class="inset-label">Do'stlarni taklif qilish</div>
              <div class="inset-sub">Har bir do'st uchun +${fmtNum(cfg.ref_reward_amount)} so'm</div>
            </div>
          </div>
          <div class="inset-right"><span>Nusxalash</span>${ico('chevronRight')}</div>
        </button>

        <button class="inset-row" id="shareRefRow">
          <div class="inset-left">
            <span class="sq-icon sq-green">${ico('share')}</span>
            <div>
              <div class="inset-label">Telegramda ulashish</div>
              <div class="inset-sub">Shaxsiy referal havolangizni yuborish</div>
            </div>
          </div>
          <div class="inset-right">${ico('chevronRight')}</div>
        </button>

        <button class="inset-row" id="dailyBonusRow">
          <div class="inset-left">
            <span class="sq-icon sq-gold">${ico('gift')}</span>
            <div>
              <div class="inset-label">Kunlik bonus olish</div>
              <div class="inset-sub">Har 24 soatda +${fmtNum(cfg.daily_reward_amount)} so'm</div>
            </div>
          </div>
          <div class="inset-right">${ico('chevronRight')}</div>
        </button>

        <button class="inset-row" id="openAiFromProfile">
          <div class="inset-left">
            <span class="sq-icon sq-ai">${ico('sparkles')}</span>
            <div>
              <div class="inset-label">Movie Land AI Yordamchi</div>
              <div class="inset-sub">Kino topish va barcha savollar bo'yicha chat</div>
            </div>
          </div>
          <div class="inset-right">${ico('chevronRight')}</div>
        </button>

        <div class="inset-row" id="themeRow" style="cursor:pointer">
          <div class="inset-left">
            <span class="sq-icon sq-slate">${ico('moon')}</span>
            <div>
              <div class="inset-label">Qorong'i rejim</div>
              <div class="inset-sub">Ko'z uchun qulay tungi ko'rinish</div>
            </div>
          </div>
          <div id="profileThemeSwitch" class="toggle-switch ${state.theme === 'dark' ? 'on' : ''}"></div>
        </div>
      </section>

      <section class="glass-block inset-group">
        <button class="inset-row" id="openChannelRow">
          <div class="inset-left">
            <span class="sq-icon sq-red">${ico('send')}</span>
            <div>
              <div class="inset-label">Rasmiy kanal (@movieee_land)</div>
              <div class="inset-sub">Barcha yangi premyeralar va kodlar</div>
            </div>
          </div>
          <div class="inset-right">${ico('chevronRight')}</div>
        </button>
        <button class="inset-row" id="openGroupRow">
          <div class="inset-left">
            <span class="sq-icon sq-blue">${ico('users')}</span>
            <div>
              <div class="inset-label">Mavzuli guruh (@movieeland_group)</div>
              <div class="inset-sub">Kino buyurtmalari va muhokamalar</div>
            </div>
          </div>
          <div class="inset-right">${ico('chevronRight')}</div>
        </button>
      </section>
    `;

    host.querySelectorAll('.plan-tile').forEach(btn => {
      btn.addEventListener('click', () => {
        haptic('light');
        state.selectedVipDays = Number(btn.dataset.days);
        renderProfileView();
      });
    });

    const buyBal = document.getElementById('buyVipBalanceBtn');
    if (buyBal) buyBal.addEventListener('click', () => handleBuyVip(state.selectedVipDays));

    const buyCard = document.getElementById('buyVipCardBtn');
    if (buyCard) buyCard.addEventListener('click', () => openBotLink('vip_shop'));

    const copyRow = document.getElementById('copyRefRow');
    if (copyRow) {
      copyRow.addEventListener('click', async () => {
        haptic('light');
        try {
          await navigator.clipboard.writeText(refLink);
          showToast('Referal havola nusxalandi');
        } catch (_) {
          showToast(refLink);
        }
      });
    }

    const shareRow = document.getElementById('shareRefRow');
    if (shareRow) {
      shareRow.addEventListener('click', () => {
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent("Movie Land — O'zbek tilidagi eng sara HD kinolar va seriallar!")}`;
        openExternalUrl(shareUrl);
      });
    }

    const bonusRow = document.getElementById('dailyBonusRow');
    if (bonusRow) bonusRow.addEventListener('click', () => openBotLink('earn_money'));

    const aiRow = document.getElementById('openAiFromProfile');
    if (aiRow) aiRow.addEventListener('click', () => openAiModal());

    const thRow = document.getElementById('themeRow');
    if (thRow) thRow.addEventListener('click', () => { haptic('light'); applyTheme(state.theme === 'dark' ? 'light' : 'dark'); });

    const chRow = document.getElementById('openChannelRow');
    if (chRow) chRow.addEventListener('click', () => openExternalUrl(cfg.channel_url));

    const grRow = document.getElementById('openGroupRow');
    if (grRow) grRow.addEventListener('click', () => openExternalUrl(cfg.group_url));
  }

  // ==================== MOVIE DETAIL MODAL ====================
  async function openMovieDetail(m) {
    state.activeMovie = m;
    haptic('light');
    const modal = document.getElementById('movieSheet');
    const body = document.getElementById('movieSheetBody');
    const titleEl = document.getElementById('movieSheetTitle');
    if (!modal || !body) return;

    if (titleEl) titleEl.textContent = m.is_serial ? 'Serial tafsiloti' : 'Kino tafsiloti';
    const isFav = state.favorites.has(String(m.code));
    const posterHtml = m.photo_id
      ? `<img class="detail-poster" src="${esc(m.photo_id)}" alt="${esc(m.name)}">`
      : `<div class="detail-poster poster-fallback">${ico('film')}</div>`;

    const genresTags = String(m.genre || '')
      .split(',')
      .map(x => x.trim())
      .filter(Boolean)
      .map(g => `<span class="meta-chip">${esc(g)}</span>`)
      .join('');

    body.innerHTML = `
      <div class="detail-hero">
        ${posterHtml}
        <div class="detail-info">
          <h2 class="detail-title">${esc(m.name)}</h2>
          <div class="detail-tags">
            <span class="meta-chip accent tabular">#${esc(m.code)}</span>
            <span class="meta-chip gold tabular">${ico('star')}<span>${esc(m.imdb || '8.4')}</span></span>
            <span class="meta-chip tabular">${esc(m.year || '2024')}</span>
            <span class="meta-chip">${esc(m.quality || '1080p HD')}</span>
            <span class="meta-chip">${esc(m.country || 'AQSH')}</span>
          </div>
          <div class="detail-tags">${genresTags}</div>
        </div>
      </div>

      ${m.caption ? `<p class="detail-desc">${esc(m.caption)}</p>` : ''}

      <div id="detailEpisodesWrap"></div>

      <div class="detail-actions">
        <button class="primary-btn" id="detailWatchBtn">
          ${ico('send')}
          <span>Botda tomosha qilish</span>
        </button>
        <button class="secondary-btn" id="detailFavBtn" style="padding:12px 14px;color:${isFav ? 'var(--accent)' : 'var(--text)'}">
          ${ico(isFav ? 'heartFill' : 'heart')}
        </button>
        <button class="secondary-btn" id="detailShareBtn" style="padding:12px 14px">
          ${ico('share')}
        </button>
      </div>
    `;

    modal.classList.add('open');

    document.getElementById('detailWatchBtn').addEventListener('click', () => watchMovieInBot(m.code, 1));
    document.getElementById('detailFavBtn').addEventListener('click', () => toggleFavorite(m.code));
    document.getElementById('detailShareBtn').addEventListener('click', () => {
      const link = `https://t.me/${state.config.bot_username}?start=watch_${m.code}_1`;
      const share = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(`${m.name} (${m.year}) — Movie Land`)}`;
      openExternalUrl(share);
    });

    if (m.is_serial || Number(m.episodes_count) > 1) {
      const epWrap = document.getElementById('detailEpisodesWrap');
      epWrap.innerHTML = '<div class="ep-section-title">Qismlar yuklanmoqda...</div>';
      try {
        const res = await fetch(`api.php?action=episodes&code=${encodeURIComponent(m.code)}`);
        const data = await res.json();
        const eps = (data && Array.isArray(data.episodes) && data.episodes.length)
          ? data.episodes
          : Array.from({ length: Math.max(1, Number(m.episodes_count) || 1) }, (_, i) => ({ episode_num: i + 1 }));
        epWrap.innerHTML = `
          <div class="ep-section-title">Qismni tanlang (${eps.length} ta qism)</div>
          <div class="ep-grid">
            ${eps.map(ep => `<button class="ep-btn tabular" data-ep="${ep.episode_num}">${ep.episode_num}-qism</button>`).join('')}
          </div>`;
        epWrap.querySelectorAll('.ep-btn').forEach(b => {
          b.addEventListener('click', () => watchMovieInBot(m.code, Number(b.dataset.ep)));
        });
      } catch (_) {
        epWrap.innerHTML = '';
      }
    }
  }

  function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
  }

  // ==================== FAVORITES & VIP API ====================
  async function toggleFavorite(code) {
    const c = String(code);
    haptic('light');
    if (state.favorites.has(c)) {
      state.favorites.delete(c);
      showToast("Sevimlilardan olib tashlandi");
    } else {
      state.favorites.add(c);
      showToast("Sevimlilarga saqlandi");
    }
    localStorage.setItem('ml_favs', JSON.stringify(Array.from(state.favorites)));
    const btn = document.getElementById('detailFavBtn');
    if (btn && state.activeMovie && String(state.activeMovie.code) === c) {
      const fav = state.favorites.has(c);
      btn.style.color = fav ? 'var(--accent)' : 'var(--text)';
      btn.innerHTML = ico(fav ? 'heartFill' : 'heart');
    }
    if (state.view === 'favorites') renderFavoritesView();

    if (tg && tg.initData) {
      try {
        await fetch('api.php?action=toggle_fav', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData: tg.initData, code: c }),
        });
      } catch (_) {}
    }
  }

  async function handleBuyVip(days) {
    if (!tg || !tg.initData) {
      showToast("Telegram bot ichidan ochib sotib oling");
      openBotLink('vip_shop');
      return;
    }
    const btn = document.getElementById('buyVipBalanceBtn');
    if (btn) { btn.disabled = true; btn.style.opacity = '0.7'; }
    try {
      const res = await fetch('api.php?action=buy_vip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData: tg.initData, days }),
      });
      const data = await res.json();
      if (data && data.ok) {
        haptic('heavy');
        if (state.user) {
          state.user.balance = data.new_balance;
          state.user.is_premium = true;
          state.user.premium_until = data.premium_until;
        }
        showToast(`${days} kunlik VIP muvaffaqiyatli faollashtirildi!`);
        renderProfileView();
      } else if (data && data.error === 'insufficient_balance') {
        showToast(`Balans yetarli emas! Yana ${fmtNum(data.needed)} so'm kerak.`);
      } else {
        showToast("Xatolik yuz berdi. Bot orqali urinib ko'ring.");
      }
    } catch (_) {
      showToast("Server bilan aloqa xatosi");
    } finally {
      if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
    }
  }

  // ==================== MOVIE LAND AI CHAT MODAL ====================
  function openAiModal(prefill = '') {
    haptic('light');
    const modal = document.getElementById('aiSheet');
    if (!modal) return;
    modal.classList.add('open');
    if (!state.chatHistory.length) {
      appendChatBubble('bot', `Assalomu alaykum! Men Movie Land AI yordamchisiman. Bazadagi ${state.movies.length} ta kino/serial ichidan xohlaganingizni topib beraman yoki VIP, balans va bonuslar bo'yicha yordam beraman.`);
    }
    const inp = document.getElementById('aiInput');
    if (inp) {
      if (prefill && prefill.trim()) {
        inp.value = prefill.trim();
        sendAiMessage();
      } else {
        setTimeout(() => inp.focus(), 100);
      }
    }
  }

  function appendChatBubble(role, text, movies = []) {
    const feed = document.getElementById('aiFeed');
    if (!feed) return;
    const b = document.createElement('div');
    b.className = `chat-bubble ${role}`;
    b.textContent = text;
    feed.appendChild(b);

    if (movies && movies.length) {
      const rail = document.createElement('div');
      rail.className = 'chat-movies';
      rail.innerHTML = movies.map(m => `
        <div class="chat-mcard" data-code="${esc(m.code)}">
          ${m.photo_id ? `<img src="${esc(m.photo_id)}" alt="${esc(m.name)}" loading="lazy">` : `<div style="height:148px;display:flex;align-items:center;justify-content:center;background:#1c1c1e">${ico('film')}</div>`}
          <div class="chat-mcard-meta">
            <div class="chat-mcard-title">${esc(m.name)}</div>
            <div class="chat-mcard-sub tabular">#${esc(m.code)} • ${esc(m.year || '')}</div>
          </div>
        </div>
      `).join('');
      rail.querySelectorAll('.chat-mcard').forEach(card => {
        card.addEventListener('click', () => {
          const found = state.movies.find(x => String(x.code) === String(card.dataset.code))
            || movies.find(x => String(x.code) === String(card.dataset.code));
          if (found) { closeModal('aiSheet'); openMovieDetail(found); }
        });
      });
      feed.appendChild(rail);
    }
    feed.scrollTop = feed.scrollHeight;
  }

  async function sendAiMessage() {
    const inp = document.getElementById('aiInput');
    if (!inp) return;
    const text = inp.value.trim();
    if (!text) return;
    inp.value = '';
    haptic('light');

    appendChatBubble('user', text);
    const typing = document.createElement('div');
    typing.className = 'chat-bubble bot';
    typing.textContent = 'Yozmoqda...';
    const feed = document.getElementById('aiFeed');
    feed.appendChild(typing);
    feed.scrollTop = feed.scrollHeight;

    try {
      const res = await fetch('api.php?action=ai_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          initData: tg ? tg.initData : '',
          history: state.chatHistory.slice(-8),
        }),
      });
      const data = await res.json();
      typing.remove();
      const reply = (data && data.reply) ? data.reply : "Javob olib bo'lmadi. Qayta urinib ko'ring.";
      const movies = (data && Array.isArray(data.movies)) ? data.movies : [];
      state.chatHistory.push({ role: 'user', text });
      state.chatHistory.push({ role: 'bot', text: reply });
      if (state.chatHistory.length > 16) state.chatHistory = state.chatHistory.slice(-16);
      appendChatBubble('bot', reply, movies);
    } catch (_) {
      typing.remove();
      appendChatBubble('bot', "Server bilan aloqa uzildi. Iltimos, birozdan so'ng qayta urinib ko'ring.");
    }
  }

  // ==================== FILTER SHEET ====================
  function openFilterSheet() {
    haptic('light');
    const modal = document.getElementById('filterSheet');
    if (!modal) return;
    modal.querySelectorAll('[data-ftype]').forEach(b => b.classList.toggle('active', b.dataset.ftype === state.filterType));
    modal.querySelectorAll('[data-sort]').forEach(b => b.classList.toggle('active', b.dataset.sort === state.sortMode));
    modal.classList.add('open');
  }

  // ==================== BOOTSTRAP & AUTH ====================
  async function loadBootstrap() {
    try {
      const res = await fetch('api.php?action=bootstrap', { cache: 'no-store' });
      const data = await res.json();
      if (data && data.ok) {
        state.config = Object.assign(state.config, data.config || {});
        state.stats = data.stats || state.stats;
        state.movies = Array.isArray(data.movies) ? data.movies : [];
        state.genres = Array.isArray(data.genres) ? data.genres : [];
        state.trailers = Array.isArray(data.trailers) ? data.trailers : [];
      }
    } catch (_) {
      showToast("Katalog yuklanmadi — qayta urinib ko'ring");
    }

    const titleEl = document.getElementById('brandTitle');
    const subEl = document.getElementById('brandSub');
    if (titleEl) titleEl.textContent = state.config.webapp_title || 'Movie Land';
    if (subEl) subEl.textContent = `${state.movies.length} ta kino • O'zbek tilida`;

    const bannerEl = document.getElementById('bannerStrip');
    if (bannerEl && state.config.webapp_banner) {
      bannerEl.innerHTML = `${ico('sparkles')}<span>${esc(state.config.webapp_banner)}</span>`;
      bannerEl.classList.add('show');
    }

    renderGenrePills();
    renderTrailers();
    renderHomeGrid();
    if (state.view === 'genres') renderGenresView();
    if (state.view === 'profile') renderProfileView();
  }

  async function authenticateUser() {
    if (!tg || !tg.initData) return;
    try {
      const res = await fetch('api.php?action=auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData: tg.initData }),
      });
      const data = await res.json();
      if (data && data.ok && data.user) {
        state.user = data.user;
        if (Array.isArray(data.user.favorites)) {
          state.favorites = new Set(data.user.favorites.map(String));
          localStorage.setItem('ml_favs', JSON.stringify(Array.from(state.favorites)));
        }
        if (state.view === 'profile') renderProfileView();
        if (state.view === 'favorites') renderFavoritesView();
      }
    } catch (_) {}
  }

  // ==================== INIT EVENTS ====================
  function initUI() {
    // Inject crisp SVG icons into static shell buttons
    document.querySelectorAll('[data-ico]').forEach(el => {
      el.innerHTML = ico(el.dataset.ico);
    });

    applyTheme(state.theme);

    // Navigation bindings
    document.querySelectorAll('[data-nav]').forEach(btn => {
      btn.addEventListener('click', () => {
        haptic('light');
        setView(btn.dataset.nav);
      });
    });

    // Top bar actions
    document.getElementById('themeBtn')?.addEventListener('click', () => {
      haptic('light');
      applyTheme(state.theme === 'dark' ? 'light' : 'dark');
    });
    document.getElementById('bonusTopBtn')?.addEventListener('click', () => setView('profile'));
    document.getElementById('aiTopBtn')?.addEventListener('click', () => openAiModal());
    document.getElementById('aiFab')?.addEventListener('click', () => openAiModal());
    document.getElementById('filterBtn')?.addEventListener('click', openFilterSheet);
    document.getElementById('searchTopBtn')?.addEventListener('click', () => setView('search'));
    document.getElementById('heroBotBtn')?.addEventListener('click', () => openBotLink(''));
    document.getElementById('seeAllHomeBtn')?.addEventListener('click', () => setView('search'));

    // Hero Search
    const heroInp = document.getElementById('heroSearchInput');
    const heroClr = document.getElementById('heroSearchClear');
    const heroGo = document.getElementById('heroSearchGo');
    if (heroInp) {
      heroInp.addEventListener('input', () => {
        state.searchQuery = heroInp.value;
        if (heroClr) heroClr.classList.toggle('show', heroInp.value.length > 0);
        renderHomeGrid();
      });
      heroInp.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); renderHomeGrid(); }
      });
    }
    if (heroClr) {
      heroClr.addEventListener('click', () => {
        heroInp.value = '';
        state.searchQuery = '';
        heroClr.classList.remove('show');
        renderHomeGrid();
      });
    }
    if (heroGo) heroGo.addEventListener('click', () => renderHomeGrid());

    // Search View input
    const spInp = document.getElementById('searchPageInput');
    const spClr = document.getElementById('searchPageClear');
    if (spInp) {
      spInp.addEventListener('input', () => {
        state.searchQuery = spInp.value;
        if (heroInp) heroInp.value = spInp.value;
        if (spClr) spClr.classList.toggle('show', spInp.value.length > 0);
        renderSearchView();
      });
    }
    if (spClr) {
      spClr.addEventListener('click', () => {
        spInp.value = '';
        state.searchQuery = '';
        if (heroInp) heroInp.value = '';
        spClr.classList.remove('show');
        renderSearchView();
      });
    }

    // Modal backdrops & close buttons
    document.querySelectorAll('.sheet-backdrop').forEach(bg => {
      bg.addEventListener('click', e => {
        if (e.target === bg) bg.classList.remove('open');
      });
    });
    document.querySelectorAll('[data-close]').forEach(btn => {
      btn.addEventListener('click', () => closeModal(btn.dataset.close));
    });

    // Filter sheet chips
    document.querySelectorAll('[data-ftype]').forEach(b => {
      b.addEventListener('click', () => {
        state.filterType = b.dataset.ftype;
        openFilterSheet();
        renderGenrePills();
        renderHomeGrid();
        if (state.view === 'search') renderSearchView();
      });
    });
    document.querySelectorAll('[data-sort]').forEach(b => {
      b.addEventListener('click', () => {
        state.sortMode = b.dataset.sort;
        openFilterSheet();
        renderHomeGrid();
        if (state.view === 'search') renderSearchView();
      });
    });

    // AI Chat submit & quick chips
    document.getElementById('aiSendBtn')?.addEventListener('click', sendAiMessage);
    document.getElementById('aiInput')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); sendAiMessage(); }
    });
    document.querySelectorAll('.ai-chip').forEach(ch => {
      ch.addEventListener('click', () => {
        const inp = document.getElementById('aiInput');
        if (inp) { inp.value = ch.textContent; sendAiMessage(); }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadBootstrap();
    authenticateUser();
  });
})();
