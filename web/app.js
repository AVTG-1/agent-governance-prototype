// Agent governance console, in the proposal deck's visual language.
// The UI is a pure function of the event log:
//   state = events.reduce(apply, initialState());  render(state)
// Live mode folds events as they stream in; a key view folds the same log up to a marker.
// When window.__REPLAY__ is present (the exported key-views file) nothing touches the network.
//
// Layout: the agent-action map (left, the focal point), the act panel (right), then the caption and a
// one-row decision ticker. Nothing scrolls during autoplay; the full timeline is a drawer (L).

const REPLAY = window.__REPLAY__ || null;
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clone = (o) => JSON.parse(JSON.stringify(o));
const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const ACT_VIEW = { 1: 'registry', 2: 'onboard', 3: 'rulebook', 4: 'enforce', 5: 'attack', 6: 'harden', 7: 'extra' };
const ACT_FALLBACK = { 1: 'Discover', 2: 'Shadow and learn', 3: 'People sign', 4: 'Enforce', 5: 'Attack', 6: 'Tighten and prove' };
const ACT_COLOR = { 1: 'var(--brand)', 2: 'var(--ai)', 3: 'var(--hold)', 4: 'var(--allow)', 5: 'var(--deny)', 6: 'var(--brand)' };
const JOB_SHORT = { rulebook: 'Rulebook', plan: 'Plan', case: 'Case', diff: 'Hardening' };

// ---------------------------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------------------------

function initialState() {
  return {
    runId: null, models: {}, provider: null, startedAt: null, end: 300, speed: 1, labels: {}, acts: {}, neededAt: {},
    t: 0, act: 0, actTitle: '', gist: '', deck: null, intro: null, lastSeq: 0, caption: '', captionSeq: 0,
    waiting: null, paused: false, pauseReason: null, error: null, approval: null,
    done: false, closed: false, extraDone: false, policy: null, enforce: false,
    map: { mode: 'idle', plane: false, agents: {}, edges: {}, usageMax: 1, focus: [], focusSeq: 0, last: null },
    timeline: [], panelView: null, panels: {}, llm: {}, keyviews: [],
  };
}

function edgeOf(s, agent, system) {
  const k = `${agent}|${system}`;
  if (!s.map.edges[k]) s.map.edges[k] = { key: k, agent, system, week: 0, state: 'unknown', seq: 0, would: null };
  return s.map.edges[k];
}

function apply(s, ev) {
  const p = ev.payload || {};
  s.lastSeq = ev.seq;
  s.t = ev.t;
  if (ev.kind !== 'run' && ev.act) s.act = ev.act;
  switch (ev.kind) {
    case 'run': {
      const n = initialState();
      Object.assign(n, { runId: p.run_id, models: p.models, provider: p.provider, startedAt: p.started_at,
        speed: p.speed, end: p.end, lastSeq: ev.seq, labels: p.labels || {}, acts: p.acts || {}, neededAt: p.needed_at || {} });
      return n;
    }
    case 'act':
      s.act = p.act; s.actTitle = p.title; s.gist = p.gist || ''; s.deck = p.deck || null;
      s.intro = p.intro ? { act: p.act, title: p.title, sub: p.sub, deck: p.deck, gist: p.gist } : null;
      s.panelView = ACT_VIEW[p.act] || s.panelView;
      break;
    case 'caption':
      s.caption = p.text; s.captionSeq = ev.seq; break;
    case 'panel': {
      const o = (s.panels[p.view] = { ...(s.panels[p.view] || {}), ...clone(p.set || {}) });
      for (const [k, item] of Object.entries(p.push || {})) o[k] = [...(o[k] || []), clone(item)];
      if (p.show !== false) s.panelView = p.view;
      break;
    }
    case 'map': {
      const m = s.map;
      if (p.set) {
        if (p.set.mode === 'governed' && m.mode === 'ungoverned') {     // leaving today mode: bypass lines go
          for (const e of Object.values(m.edges)) if (e.state === 'bypass') { e.state = e.prev || 'observed'; e.harmful = false; }
        }
        Object.assign(m, p.set);
      }
      if (p.agent) m.agents[p.agent.id] = { ...(m.agents[p.agent.id] || { id: p.agent.id }), ...clone(p.agent) };
      for (const [a, sys] of p.links || []) edgeOf(s, a, sys);
      if (p.usage) {
        for (const [a, per] of Object.entries(p.usage)) {
          for (const [sys, n] of Object.entries(per)) {
            const e = edgeOf(s, a, sys);
            e.week = n;
            if (e.state === 'unknown') e.state = 'observed';
            m.usageMax = Math.max(m.usageMax, n);
          }
        }
      }
      if (p.edge) { const e = edgeOf(s, p.edge.agent, p.edge.system); Object.assign(e, clone(p.edge)); e.seq = ev.seq; }
      if (p.focus) { m.focus = [...p.focus]; m.focusSeq = ev.seq; }
      break;
    }
    case 'decision':
    case 'call': {
      const row = { ...clone(p), seq: ev.seq, t: ev.t, act: ev.act, kind: ev.kind, hash: ev.hash, prev_hash: ev.prev_hash };
      s.timeline.push(row);
      const chain = p.chain && p.chain.length ? p.chain : [p.agent];
      const e = edgeOf(s, chain[0], p.system || 'external');
      if (ev.kind === 'call') {
        if (e.state !== 'bypass') e.prev = e.state;
        e.state = 'bypass'; e.harmful = !!p.harmful;
      } else if (p.mode === 'shadow') {
        if (e.state === 'unknown') e.state = 'observed';
        if (p.decision === 'would_deny') e.would = 'stop';
        else if (p.decision === 'would_hold' && e.would !== 'stop') e.would = 'wait';
      } else if (e.state !== 'rejected' || p.decision !== 'deny') {
        e.state = p.decision === 'allow' ? 'allow' : p.decision === 'hold' ? 'hold' : 'deny';
      }
      e.seq = ev.seq;
      s.map.last = { seq: ev.seq, kind: ev.kind, key: e.key, mode: ev.kind === 'call' ? 'ungoverned' : p.mode, decision: p.decision,
        rule: p.rule, chain, agent: p.agent, system: p.system, capability: p.capability, harmful: !!p.harmful };
      break;
    }
    case 'llm':
      if (p.job) s.llm[p.job] = { ...(s.llm[p.job] || {}), ...clone(p) };
      break;
    case 'system':
      if ('waiting' in p) s.waiting = p.waiting ? { role: p.waiting, job: p.job, since: ev.t } : null;
      if ('paused' in p) { s.paused = p.paused; s.pauseReason = p.paused ? p.reason : null; }
      if ('speed' in p) s.speed = p.speed;
      if ('policy' in p) s.policy = p.policy;
      if ('enforce' in p) s.enforce = p.enforce;
      if ('models' in p) s.models = { ...s.models, ...p.models };
      if ('intro' in p && !p.intro) s.intro = null;
      if ('deck' in p) s.deck = p.deck;
      if ('approval' in p) s.approval = p.approval ? clone(p.approval) : null;
      if (p.done) s.done = true;
      if (p.closed) s.closed = true;
      if (p.extra_done) s.extraDone = true;
      break;
    case 'error':
      s.error = p.message ? { ...p } : null; break;
    case 'keyview':
      s.keyviews.push({ ...clone(p), seq: ev.seq, ts: ev.ts }); break;
    default:
      break;
  }
  return s;
}

const fold = (events) => events.reduce(apply, initialState());

// ---------------------------------------------------------------------------------------------
// View state (not story state): theme, overlays, filters, key-view position, the live clock
// ---------------------------------------------------------------------------------------------

const ui = {
  state: initialState(), kvData: null, kv: null, film: false, drawer: null, closeHidden: false, filter: null,
  catalog: null, conn: null, gate: { provider: 'foundry', busy: false, starting: false, preflight: false },
  frame: 0, animSeq: 0, clock: { t: 0, at: 0 }, stream: 'idle', switchPick: null, busy: false,
};

let CONSOLE_ID = '';
try { CONSOLE_ID = sessionStorage.getItem('agentgov-console') || ''; } catch (e) { /* storage unavailable */ }
if (!CONSOLE_ID) {
  CONSOLE_ID = `c-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
  try { sessionStorage.setItem('agentgov-console', CONSOLE_ID); } catch (e) { /* a reload makes this tab a viewer */ }
}

// ---------------------------------------------------------------------------------------------
// Icons (the deck's line icons), words and small helpers
// ---------------------------------------------------------------------------------------------

const svg = (body, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
const ICON = {
  allow: svg('<path d="m4.5 12.5 4.5 4.5 10.5-11"/>'),
  deny: svg('<path d="m6 6 12 12m0-12L6 18"/>'),
  hold: svg('<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>'),
  eye: svg('<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>'),
  warn: svg('<path d="M12 3 22 20H2Z"/><path d="M12 9.5v4.5M12 17.2v.1"/>'),
  ai: svg('<path d="M12 3l1.8 4.9L19 9.7l-5.2 1.8L12 16.5l-1.8-5L5 9.7l5.2-1.8Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z"/>'),
  lock: svg('<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.6v.1"/>'),
  sim: svg('<circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/>'),
  pause: svg('<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>', 'i fill'),
  play: svg('<path d="M6 4v16l14-8Z"/>', 'i fill'),
  next: svg('<path d="M5 4v16l11-8Z"/><rect x="17" y="4" width="3" height="16" rx="1"/>', 'i fill'),
  restart: svg('<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3 3.5v5h5"/>'),
  moon: svg('<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>'),
  prev: svg('<path d="m15 5-7 7 7 7"/>'), fwd: svg('<path d="m9 5 7 7-7 7"/>'), close: svg('<path d="m6 6 12 12m0-12L6 18"/>'),
  book: svg('<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2Z"/><path d="M4 19a2 2 0 0 1 2-2h13"/>'),
  key: svg('<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 9.3-9.3M16 7l3 3M14 9l2 2"/>'),
  list: svg('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'),
  route: svg('<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H17a3.5 3.5 0 0 0 0-7H7a3.5 3.5 0 0 1 0-7h8.5"/>'),
  sign: svg('<path d="M20 20H4"/><path d="m14.5 4.5 5 5L9 20H4v-5Z"/>'),
  person: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  agent: svg('<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>'),
  monitor: svg('<path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/><path d="M4 6h.01"/><path d="M2.29 9.62A10 10 0 1 0 21.31 8.35"/><path d="M16.24 7.76A6 6 0 1 0 8.23 16.67"/><path d="M12 18h.01"/><path d="M17.99 11.66A6 6 0 0 1 15.77 16.67"/><circle cx="12" cy="12" r="2"/><path d="m13.41 10.59 5.66-5.66"/>'),
  identity: svg('<path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/><path d="M14 13.12c0 2.38 0 6.38-1 8.88"/><path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/><path d="M2 12a10 10 0 0 1 18-6"/><path d="M2 16h.01"/><path d="M21.8 16c.2-2 .131-5.354 0-6"/><path d="M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2"/><path d="M8.65 22c.21-.66.45-1.32.57-2"/><path d="M9 6.8a6 6 0 0 1 9 5.2v2"/>'),
  policy: svg('<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'),
  jit: svg('<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/>'),
  enforce: svg('<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>'),
  systems: svg('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>'),
  evidence: svg('<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 15 2 2 4-4"/>'),
};

const DECISION_TAG = {
  allow: ['tag-allow', 'allow', 'allowed'],
  deny: ['tag-deny', 'deny', 'stopped'],
  hold: ['tag-hold', 'hold', 'waits for a person'],
  would_deny: ['tag-shadow', 'eye', 'would stop'],
  would_hold: ['tag-hold', 'eye', 'would wait'],
};
function tag(decision, word) {
  const [cls, icon, w] = DECISION_TAG[decision] || ['tag-info', 'info', decision];
  return `<span class="tag ${cls}">${ICON[icon]}${esc(word || w)}</span>`;
}
const okTag = (ok, word) => `<span class="tag ${ok ? 'tag-allow' : 'tag-deny'}">${ICON[ok ? 'allow' : 'deny']}${esc(word || (ok ? 'pass' : 'fail'))}</span>`;
const aiTag = (word) => `<span class="tag tag-ai">${ICON.ai}${esc(word)}</span>`;
const simTag = (word = 'simulated') => `<span class="tag tag-sim">${ICON.sim}${esc(word)}</span>`;
const signTag = (word) => `<span class="tag tag-hold">${ICON.sign}${esc(word)}</span>`;
const mmss = (t) => { const s = Math.max(0, Math.floor(t || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const hhmm = (iso) => (iso ? String(iso).slice(11, 16) : '');
const ms = (v) => (v == null ? '—' : `${Number(v).toFixed(v < 1 ? 3 : 1)} ms`);
const secs = (v) => (v == null ? '' : `${(v / 1000).toFixed(1)} s`);
const short = (id) => String(id || '').replace('-agent', '');
const n0 = (v) => Number(v || 0).toLocaleString('en-GB');
const modelName = (ref) => String(ref || '').split(':').pop().split('/').pop();
const plural = (n, one, many) => `${n} ${n === 1 ? one : many || `${one}s`}`;

function cur() { return ui.rp ? ui.rp.state : ui.kv ? ui.kv.state : ui.state; }
const L = () => cur().labels || {};
function plain(cap) { return ((L().capabilities || {})[cap]) || cap; }
function agentName(id) { return ((L().agents || {})[id]) || short(id); }
function ruleId(ref) { return String(ref || '').split('@')[0]; }
function rulePlain(ref) { return ((L().rules || {})[ruleId(ref)]) || ''; }
function systemName(id) {
  for (const a of L().areas || []) for (const [sid, name] of a.systems) if (sid === id) return name;
  return id;
}
// Plain language first, the technical id underneath, never truncated.
const what = (cap, extra = '') => `<span class="what"><span class="pl">${esc(plain(cap))}${extra}</span><code class="tid">${esc(cap)}</code></span>`;
const decisionWord = (r) => (r.kind === 'call' ? 'unchecked' : (DECISION_TAG[r.decision] || [0, 0, r.decision])[2]);

// ---------------------------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------------------------

const cache = {};
function put(sel, html) {
  if (cache[sel] === html) return false;
  cache[sel] = html;
  const el = $(sel);
  if (el) el.innerHTML = html;
  return true;
}

function render() {
  const s = cur();
  document.body.classList.toggle('still', !!ui.kv || REDUCED);
  document.body.classList.toggle('replaying', !!ui.rp);
  put('#h-acts', renderActs(s));
  put('#h-controls', renderControls(s));
  const mapChanged = put('#map', renderMap(s));
  put('#panel', renderPanel(s));
  put('#panel-over', renderPanelOver(s));
  put('#cap-act', s.act ? esc(s.act > 6 ? 'Extra' : `Act ${s.act} · ${s.actTitle || ACT_FALLBACK[s.act] || ''}`) : 'Ready');
  put('#cap-text', esc(ui.kv ? ui.kvData.views[ui.kv.i].caption : s.caption || ''));
  const capEl = $('#cap-text');
  if (capEl && capEl.dataset.seq !== String(s.captionSeq)) {
    capEl.dataset.seq = String(s.captionSeq);
    capEl.classList.remove('fresh'); void capEl.offsetWidth; capEl.classList.add('fresh');
  }
  put('#ticker', renderTicker(s));
  fitTicker();
  put('#overlays', renderOverlays(s));
  drawEdges(s, mapChanged);
  renderReplayLayer();
  tickClock();
}

function schedule() {
  if (ui.frame) return;
  ui.frame = requestAnimationFrame(() => { ui.frame = 0; render(); });
}

// --- header: title, act stepper, clock and controls only ---

function viewer() { return !REPLAY && ui.conn && ui.conn.controller && ui.conn.controller.set && !ui.conn.controller.you; }

function renderActs(s) {
  if (ui.rp) {
    const m = ui.rp.meta || {};
    return `<span class="kv-badge">${ICON.play}Captioned replay · recorded from this run at ${esc(String(m.recorded_at || '').slice(11, 16))} · no live calls</span>`;
  }
  if (ui.kv) {
    const v = ui.kvData.views[ui.kv.i];
    return `<span class="kv-badge">${ICON.info}Key view ${v.n} of ${ui.kvData.views.length} · recorded from this run at ${esc(hhmm(v.ts))} · no live calls</span>`;
  }
  const dis = ui.kv || REPLAY || viewer() ? 'disabled' : '';
  return [1, 2, 3, 4, 5, 6].map((k, i) => {
    const title = (s.acts[k] && s.acts[k].title) || ACT_FALLBACK[k];
    const cls = k === s.act ? 'current' : k < s.act ? 'done' : '';
    const num = k < s.act ? ICON.allow : k;
    return `${i ? '<span class="sep"></span>' : ''}<button class="${cls}" data-cmd="jump:${k}" ${dis} title="Jump to act ${k}"><span class="num">${num}</span><span class="lbl">${esc(title)}</span></button>`;
  }).join('');
}

function renderControls(s) {
  if (ui.rp) {
    const r = ui.rp;
    return `<span class="clock" id="rp-time"><b>${mmss(r.pos)}</b> / ${mmss(r.total)}</span>
      <button class="ibtn${r.playing ? '' : ' on'}" data-cmd="rp-toggle" title="${r.playing ? 'Pause' : 'Play'} (Space)">${r.playing ? ICON.pause : ICON.play}</button>
      <button class="ibtn" data-cmd="rp-prev" title="Previous callout (←)">${ICON.prev}</button>
      <button class="ibtn" data-cmd="rp-next" title="Next callout (→)">${ICON.fwd}</button>
      <button class="ibtn" data-cmd="rp-restart" title="Replay from the start (R)">${ICON.restart}</button>
      <button class="btn btn-quiet" data-cmd="film">Key views <span class="kbd">K</span></button>
      <button class="btn btn-quiet" data-cmd="rp-exit">${REPLAY ? 'Stop' : 'Back'} <span class="kbd">Esc</span></button>
      <button class="ibtn" data-cmd="theme" title="Theme (D)">${ICON.moon}</button>`;
  }
  const clock = `<span class="clock" id="clock"><b>${mmss(s.t)}</b> / ${mmss(s.end)}</span>`;
  const theme = `<button class="ibtn" data-cmd="theme" title="Theme (D)">${ICON.moon}</button>`;
  if (ui.kv) {
    const i = ui.kv.i, n = ui.kvData.views.length;
    return `${clock}
      <button class="ibtn" data-cmd="kv-step:-1" ${i === 0 ? 'disabled' : ''} title="Previous key view (←)">${ICON.prev}</button>
      <button class="ibtn" data-cmd="kv-step:1" ${i === n - 1 ? 'disabled' : ''} title="Next key view (→)">${ICON.fwd}</button>
      <button class="btn btn-quiet" data-cmd="film">Key views <span class="kbd">K</span></button>
      ${REPLAY ? '' : `<button class="btn btn-quiet" data-cmd="kv-exit">Back <span class="kbd">Esc</span></button>`}${theme}`;
  }
  const kv = (s.closed || (ui.conn && ui.conn.keyviews)) ? `<button class="btn btn-primary" data-cmd="film">Key views <span class="kbd">K</span></button>` : '';
  if (viewer()) {
    return `${clock}<span class="viewer">${ICON.eye} Viewer</span><button class="btn btn-quiet" data-cmd="take-control">Take control</button>${theme}${kv}`;
  }
  if (s.done) return `${clock}<button class="ibtn" data-cmd="restart" title="Restart (R)">${ICON.restart}</button>${theme}${kv}`;
  const pp = s.paused ? `<button class="ibtn on" data-cmd="resume" title="Resume (Space)">${ICON.play}</button>`
    : `<button class="ibtn" data-cmd="pause" title="Pause (Space)">${ICON.pause}</button>`;
  const speeds = [0.5, 1, 2].map((v) => `<button role="radio" aria-checked="${s.speed === v}" data-cmd="speed:${v}" title="Speed ${v}×">${v}×</button>`).join('');
  return `${clock}${pp}<button class="ibtn" data-cmd="next" title="Next step (→)">${ICON.next}</button>
    <button class="ibtn" data-cmd="restart" title="Restart (R)">${ICON.restart}</button>
    <div class="seg" role="radiogroup" aria-label="Speed">${speeds}</div>${theme}${kv}`;
}

// The scripted clock between events: interpolated from the last event while the run plays, held while
// it waits for a model or is paused. Derived from wall time, so a background tab never drifts.
function tickClock() {
  const s = cur();
  const el = $('#clock b');
  if (!el) return;
  let t = s.t;
  if (!ui.kv && !ui.rp && !REPLAY && ui.clock.seq === s.lastSeq && !s.paused && !s.waiting && !s.done && !s.approval && s.act) {
    t = Math.min(s.end, s.t + ((performance.now() - ui.clock.at) / 1000) * (s.speed || 1));
  }
  const txt = mmss(t);
  if (el.textContent !== txt) el.textContent = txt;
}
setInterval(tickClock, 250);
document.addEventListener('visibilitychange', () => { if (!document.hidden) { for (const k of Object.keys(cache)) delete cache[k]; schedule(); } });

// --- the agent-action map: agents → the control plane → systems by business area ---

const AGENTS = ['recon-agent', 'settlement-agent', 'enrichment-agent', 'kyc-agent'];
const PARTS = [
  ['identity', 'Registry and identity'], ['policy', 'Policy decision'], ['enforce', 'Enforcement points'],
  ['jit', 'Just-in-time access'], ['monitor', 'Monitoring and investigation'], ['evidence', 'Evidence and optimisation'],
];
const PART_HELP = {
  identity: 'Who is acting, and who answers for it?', policy: 'Is this action allowed, now, for this purpose?',
  enforce: 'Where is the decision applied?', jit: 'How does an agent get an exception safely?',
  monitor: 'Is something unusual happening?', evidence: 'Can we prove it, and make it tighter over time?',
};
const DEFAULT_AREAS = [
  { id: 'front', name: 'Front office', systems: [['trade', 'Trade capture'], ['fx', 'FX positions']] },
  { id: 'middle', name: 'Middle office', systems: [['client', 'Client master']] },
  { id: 'settle', name: 'Settlement', systems: [['settlement', 'Settlement and SSIs']] },
  { id: 'recon', name: 'Reconciliation', systems: [['recon', 'Reconciliation']] },
  { id: 'ledger', name: 'Ledger and reporting', systems: [['ledger', 'General ledger']] },
  { id: 'ref', name: 'Reference data', systems: [['refdata', 'Reference data']] },
  { id: 'outside', name: 'Outside the firm', outside: true, systems: [['fileshare', 'Shared drive'], ['external', 'Internet']] },
];

function agentStatus(a) {
  const f = a.flags || [];
  if (['contained: read-only', 'session revoked', 'quarantined'].includes(a.status)) return [a.status, 'bad'];
  if (f.includes('no owner')) return ['no owner', 'bad'];
  if (f.some((x) => x.startsWith('shared with a person'))) return ['shared human login', 'bad'];
  if (a.status === 'onboarded') return [a.cred || 'onboarded', 'good'];
  if (f.includes('owner assigned')) return [`owner: ${a.owner}`, 'good'];
  if (f.some((x) => x.startsWith('direct database login'))) return ['direct database login', 'warn'];
  if (f.some((x) => x.startsWith('static API key'))) return ['static API key', 'warn'];
  if (f.some((x) => x.startsWith('cloud role'))) return ['cloud role', 'warn'];
  return [a.owner ? `owner: ${a.owner}` : 'found', ''];
}

function litParts(s) {
  const m = s.map;
  const lit = new Set(m.focus || []);
  const l = m.last;
  if (l && l.seq > m.focusSeq && l.mode !== 'ungoverned') {
    ['identity', 'policy', 'enforce'].forEach((x) => lit.add(x));
    if (ruleId(l.rule) === 'R-JIT-01') lit.add('jit');
    lit.add('evidence');
  }
  return lit;
}

function modeChip(s) {
  const m = s.map;
  if (m.mode === 'ungoverned') return `<span class="chip mode-today">${ICON.warn} Today: no control plane ${simTag()}</span>`;
  if (s.enforce) return `<span class="chip mode-enforce">${ICON.lock} Enforcing · default deny on</span>`;
  if (m.plane) return `<span class="chip">${ICON.eye} Shadow: watching, not blocking</span>`;
  return `<span class="chip">No control plane yet</span>`;
}

function renderMap(s) {
  const m = s.map;
  const lit = litParts(s);
  const areas = (L().areas && L().areas.length) ? L().areas : DEFAULT_AREAS;
  const f = ui.filter;
  const touched = new Set();
  const hot = new Set();
  for (const e of Object.values(m.edges)) {
    if (e.state === 'unknown' && !m.plane && m.mode !== 'discovery' && !Object.keys(m.agents).length) continue;
    touched.add(e.system);
    if (m.last && e.key === m.last.key) hot.add(e.system);
  }
  const agents = AGENTS.map((id) => {
    const a = m.agents[id] || { id };
    const [sub, tone] = a.known ? agentStatus(a) : ['not found yet', 'unknown'];
    const sel = f && f.agent === id ? ' selected' : '';
    const dim = f && f.agent !== id ? ' dimmed' : '';
    return `<button class="acard ${a.known ? '' : 'unknown'}${sel}${dim}" data-agent="${id}" data-cmd="filter-agent:${id}" title="Show only ${esc(agentName(id))}'s calls">
      <span class="an">${ICON.agent}${esc(agentName(id))}</span>
      <span class="as ${tone}">${esc(sub)}</span>
      ${id === 'recon-agent' && a.known ? `<span class="live">${ICON.ai}live model</span>` : ''}</button>`;
  }).join('');
  const inv = Object.values(s.llm).find((x) => x.role === 'investigator' && x.status === 'requested');
  const band = PARTS.map(([id, name]) => `<div class="part${lit.has(id) ? ' lit' : ''}" data-part="${id}" title="${esc(PART_HELP[id])}">${ICON[id].replace('class="i"', 'class="i pi"')}<span>${esc(name)}</span></div>`).join('');
  const sysChip = (id, name) => {
    const st = m.last && m.last.system === id ? ` st-${m.last.kind === 'call' ? (m.last.harmful ? 'leak' : 'today') : (m.last.decision || '').replace('would_', 'w')}` : '';
    return `<span class="schip${touched.has(id) ? ' known' : ''}${hot.has(id) ? ' hot' : ''}${st}${f && f.system === id ? ' selected' : ''}" data-sys="${id}">${esc(name)}</span>`;
  };
  const areaCards = areas.map((a) => `<div class="area${a.outside ? ' outside' : ''}"><span class="at">${a.outside ? ICON.warn : ''}${esc(a.name)}</span><div class="chips">${a.systems.map(([id, n]) => sysChip(id, n)).join('')}</div></div>`).join('');
  const filt = f ? `<button class="chip filter" data-cmd="filter-clear" title="Show all calls">Showing: ${esc(agentName(f.agent))}${f.system ? ` → ${esc(systemName(f.system))}` : ''} ${ICON.close}</button>` : '';
  const off = !m.plane ? ' off' : m.mode === 'ungoverned' ? ' bypassed' : '';
  return `<div class="amap-head"><h2>Who reaches what</h2>${f ? '' : '<span class="dim xs">Kaiyo Securities · synthetic</span>'}<span class="grow"></span>${filt}${modeChip(s)}</div>
    <div class="amap-body" id="amap-body">
      <div class="col col-agents"><span class="ct">Agents</span>${agents}
        <div class="inv${inv ? ' busy' : ''}">${ICON.ai}<span><b>AI investigator</b>${inv ? 'drafting…' : 'advises only · no access'}</span></div></div>
      <div class="col col-plane"><span class="ct">Control plane</span><div class="band${off}">${band}
        ${!m.plane ? '<span class="band-note">not in place yet</span>' : m.mode === 'ungoverned' ? '<span class="band-note bad">today: bypassed</span>' : ''}</div></div>
      <div class="col col-systems"><span class="ct">Systems by business area</span>${areaCards}</div>
      <svg class="edges" id="edges" aria-hidden="true"></svg>
    </div>
    ${renderLegend(s)}`;
}

function renderLegend(s) {
  const st = new Set(Object.values(s.map.edges).map((e) => e.state));
  const items = [];
  if (st.has('unknown')) items.push('<span><i class="ln unknown"></i>Reach found, never checked</span>');
  if (st.has('observed') || st.has('rejected')) items.push('<span><i class="ln observed"></i>Observed in shadow (thicker = used more)</span>');
  items.push('<span><i class="ln allow"></i>Allowed</span><span><i class="ln deny"></i>Stopped at the plane</span><span><i class="ln hold"></i>Waits for a person</span>');
  if (st.has('bypass')) items.push('<span><i class="ln bypass"></i>Today: no check (simulated)</span>');
  items.push('<span><i class="sq ai"></i>AI, advisory only</span>');
  return `<div class="legend">${items.join('')}</div>`;
}

// Edges are drawn after layout, from the cards' positions: agent → band → system. Presentation only.
function drawEdges(s, mapChanged) {
  const body = $('#amap-body');
  const svgEl = $('#edges');
  if (!body || !svgEl) return;
  const key = `${s.lastSeq}|${ui.filter ? ui.filter.agent + ui.filter.system : ''}|${body.clientWidth}x${body.clientHeight}|${!!ui.kv}`;
  if (!mapChanged && svgEl.dataset.key === key) return;
  svgEl.dataset.key = key;
  const base = body.getBoundingClientRect();
  const W = base.width, H = base.height;
  svgEl.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const m = s.map;
  const band = $('.band', body).getBoundingClientRect();
  const bl = band.left - base.left, br = band.right - base.left, bt = band.top - base.top + 6, bb = band.bottom - base.top - 6;
  const rect = (el) => { const r = el.getBoundingClientRect(); return { l: r.left - base.left, r: r.right - base.left, y: r.top - base.top + r.height / 2 }; };
  const clampY = (y) => Math.max(bt, Math.min(bb, y));
  const out = [];
  const anims = [];
  const f = ui.filter;
  const edges = Object.values(m.edges).sort((a, b) => a.seq - b.seq);
  for (const e of edges) {
    const aEl = $(`[data-agent="${e.agent}"]`, body), sEl = $(`[data-sys="${e.system}"]`, body);
    if (!aEl || !sEl || !(m.agents[e.agent] && m.agents[e.agent].known)) continue;
    const a = rect(aEl), b = rect(sEl);
    const x0 = a.r + 2, y0 = a.y, x1 = b.l - 2, y1 = b.y;
    const yi = clampY(y0 + (y1 - y0) * 0.25), yo = clampY(y1 + (y0 - y1) * 0.25);
    const c1 = Math.max(18, (bl - x0) * 0.5), c2 = Math.max(18, (x1 - br) * 0.5);
    const inSeg = `M${x0},${y0} C${x0 + c1},${y0} ${bl - c1},${yi} ${bl},${yi}`;
    const outSeg = `M${br},${yo} C${br + c2},${yo} ${x1 - c2},${y1} ${x1},${y1}`;
    const direct = `M${x0},${y0} C${(x0 + x1) / 2},${y0} ${(x0 + x1) / 2},${y1} ${x1},${y1}`;
    const w = e.week ? 1.4 + 5 * Math.sqrt(e.week / (m.usageMax || 1)) : 2;
    const latest = m.last && m.last.key === e.key;
    const dim = f && (f.agent !== e.agent || (f.system && f.system !== e.system)) ? ' faded' : '';
    let cls = e.state, d, marker = '';
    if (!m.plane || e.state === 'unknown') { cls = 'unknown'; d = direct; }
    else if (e.state === 'bypass') { cls = e.harmful ? 'bypass harm' : 'bypass'; d = direct; }
    else if (e.state === 'observed' || e.state === 'allow') { d = `${inSeg} ${outSeg}`; }
    else {                                           // deny, hold, rejected: the line stops at the plane
      d = inSeg;
      const mk = e.state === 'hold' ? 'hold' : 'deny';
      marker = `<g class="mk ${mk}" transform="translate(${bl},${yi})"><circle r="8"/>${mk === 'hold'
        ? '<path d="M-2.5,-3.5v7M2.5,-3.5v7"/>' : '<path d="M-3.2,-3.2l6.4,6.4M3.2,-3.2l-6.4,6.4"/>'}</g>`;
      if (e.state === 'rejected') marker += `<text class="mk-label" x="${bl - 10}" y="${yi - 12}" text-anchor="end">rejected by the owner</text>`;
    }
    if (e.would && e.state === 'observed') {
      marker += `<g class="mk would ${e.would}" transform="translate(${bl - 14},${yi})"><circle r="6"/></g>`;
    }
    out.push(`<path class="edge ${cls}${latest ? ' latest' : ''}${dim}" d="${d}" style="stroke-width:${latest ? w + 1.5 : w}px"/>${marker}`);
    out.push(`<path class="hit" d="${d}" data-cmd="filter-edge:${e.agent}|${e.system}"><title>${esc(agentName(e.agent))} → ${esc(systemName(e.system))}${e.week ? ` · ${n0(e.week)} calls in the recorded week` : ''}</title></path>`);
    if (latest && !ui.kv && !REDUCED && m.last.seq > ui.animSeq) anims.push({ d: d.replace(/ M/g, ' L'), cls });
  }
  // Agent to agent: the delegated hop of the latest decision.
  const l = m.last;
  if (l && l.chain && l.chain.length > 1) {
    const aEl = $(`[data-agent="${l.chain[0]}"]`, body), bEl = $(`[data-agent="${l.chain[l.chain.length - 1]}"]`, body);
    if (aEl && bEl) {
      const a = aEl.getBoundingClientRect(), b = bEl.getBoundingClientRect();
      const x = a.left - base.left - 4, y0 = a.top - base.top + a.height / 2, y1 = b.top - base.top + b.height / 2;
      out.push(`<path class="edge delegate ${l.decision === 'deny' ? 'deny' : 'allow'}" d="M${x},${y0} C${x - 26},${y0} ${x - 26},${y1} ${x},${y1}"/>`);
    }
  }
  if (anims.length) {
    ui.animSeq = m.last.seq;
    const a = anims[0];
    out.push(`<circle class="dot ${a.cls}" r="5"><animateMotion dur="0.9s" fill="freeze" path="${a.d}"/></circle>`);
  }
  svgEl.innerHTML = out.join('');
}

// --- the ticker: the last few decisions as plain-language pills, model readiness on the right ---

function rowsFor(s) {
  const f = ui.filter;
  return s.timeline.filter((r) => !f || ((r.chain && r.chain.length ? r.chain[0] : r.agent) === f.agent && (!f.system || r.system === f.system)));
}

function pill(r) {
  const who = short(r.chain && r.chain.length ? r.chain[0] : r.agent);
  const cls = r.kind === 'call' ? (r.harmful ? 'deny today' : 'today') : (DECISION_TAG[r.decision] || ['tag-info'])[0].replace('tag-', '');
  const rule = r.kind === 'call' ? 'no control' : ruleId(r.rule);
  return `<button class="pill ${cls}" data-cmd="record:${r.seq}" title="${esc(r.capability)} · ${esc(r.reason || r.outcome || '')}">
    <b>${esc(who)}</b> · ${esc(plain(r.capability))} → <b class="dw">${esc(decisionWord(r))}</b> · <span class="mono">${esc(rule)}</span></button>`;
}

function renderTicker(s) {
  const rows = rowsFor(s).slice(-4).reverse();
  const none = ui.filter ? 'No decision recorded for this selection yet (shadow allows are counted, not listed)'
    : s.map.plane ? 'No decisions yet' : 'No control plane yet: nothing is decided or recorded';
  const pills = rows.length ? rows.map(pill).join('') : `<span class="none">${none}</span>`;
  const jobs = ['rulebook', 'plan', 'case', 'diff'];
  const lights = s.runId ? jobs.map((j) => {
    const x = s.llm[j] || { status: 'pending' };
    const need = s.neededAt[j] != null ? mmss(s.neededAt[j]) : '';
    const word = { pending: 'not sent yet', requested: 'in flight', ready: 'ready', used: 'used', failed: 'failed' }[x.status] || x.status;
    return `<span class="light ${esc(x.status)}" title="${esc(JOB_SHORT[j])} call (${esc(x.role || '')}, ${esc(x.model || '')}): ${esc(word)}${need ? ` · needed at ${need}` : ''}${x.latency_ms ? ` · ${secs(x.latency_ms)}` : ''}"><i></i>${esc(JOB_SHORT[j])}</span>`;
  }).join('') : '';
  const conn = !REPLAY && ui.stream === 'lost' ? `<span class="conn">${ICON.warn} reconnecting…</span>` : '';
  return `<button class="btn btn-quiet tk-log" data-cmd="log" title="All decisions (L)">${ICON.list}All decisions <span class="kbd">L</span></button>
    <div class="pills" id="pills">${pills}</div>
    <div class="lights">${conn}${lights ? `<span class="lt">${ICON.ai}Live model calls</span>${lights}` : ''}</div>`;
}

// Show only the pills that fit whole; never a clipped pill.
function fitTicker() {
  const box = $('#pills');
  if (!box) return;
  const kids = [...box.children];
  kids.forEach((k) => { k.hidden = false; });
  const right = box.getBoundingClientRect().right;
  let hide = false;
  for (const k of kids) {
    if (hide || k.getBoundingClientRect().right > right + 0.5) { k.hidden = true; hide = true; }
  }
}

// --- the act panel: one card per beat; a big number or a short list; one line of explanation ---

function pHead(s, title, sub, right = '') {
  const act = s.act > 6 ? 'Extra' : `Act ${s.act} · ${esc(s.actTitle || ACT_FALLBACK[s.act] || '')}`;
  const chips = [];
  if (s.policy) chips.push(`<span class="chip">${ICON.lock}<b>${esc(s.policy)}</b></span>`);
  if (s.deck) chips.push(`<span class="chip deck">${ICON.book}Deck: ${esc(s.deck)}</span>`);
  return `<div class="p-head"><div class="p-meta"><span class="kicker" style="--actc:${ACT_COLOR[s.act] || 'var(--brand)'}">${act}</span>${chips.join('')}</div>
    <div class="p-title"><h2>${esc(title)}</h2>${right}</div>${sub ? `<p class="p-sub">${esc(sub)}</p>` : ''}</div>`;
}

const stat = (big, label, cls = '') => `<div class="stat ${cls}"><b>${big}</b><span>${label}</span></div>`;

function renderPanel(s) {
  const v = s.panelView;
  const p = s.panels[v] || {};
  switch (v) {
    case 'registry': return panelRegistry(s, p);
    case 'onboard': return panelOnboard(s, p);
    case 'shadow': return panelShadow(s, p);
    case 'rulebook': return panelRulebook(s, p);
    case 'enforce': return panelEnforce(s, p);
    case 'attack': return panelAttack(s, p);
    case 'harden': return panelHarden(s, p);
    case 'evidence': return panelEvidence(s, p);
    case 'extra': return panelExtra(s, p);
    default: return `${pHead(s, 'Policy decides. AI advises. People approve.', 'The story starts in a moment.')}`;
  }
}

function panelRegistry(s, p) {
  const rows = p.rows || [];
  const out = [pHead(s, 'Find every agent', 'Registry and identity: what runs, on what credential, and who answers for it.',
    p.scanning ? '<span class="tag tag-brand pulse">scanning</span>' : rows.length ? `<span class="tag tag-info">${rows.length} agents</span>` : '')];
  if (p.scanning || !rows.length) {
    out.push(`<div class="sources">${(p.sources || []).map((x) => `<div class="src"><b>${x.count == null ? '…' : x.count}</b><span>${esc(x.name)}</span></div>`).join('')}</div>
      <p class="note">Correlating signals across the estate. Deterministic; no AI.</p>`);
  }
  if (rows.length) {
    const finding = Object.fromEntries((p.findings || []).map((f) => [f.agent, f.text]));
    out.push(`<div class="rows">${rows.map((r) => {
      const credBad = ['shared', 'static-key', 'db-login'].includes(r.credential_kind);
      const owner = r.owner ? `${esc(r.owner)}${r.owner_source === 'assigned' ? ` ${tag('allow', 'assigned by rule')}` : ''}` : tag('deny', 'no owner');
      const hl = finding[r.id] && !(r.owner_source === 'assigned' && r.id === p.assigned) ? ' hl' : '';
      return `<div class="row${hl}${p.assigned === r.id ? ' assigned' : ''}"><div class="rn"><b>${esc(agentName(r.id))}</b><code class="tid">${esc(r.id)}</code></div>
        <div class="rc"><span class="lbl">Owner</span>${owner}</div><div class="rc"><span class="lbl">Credential</span><span class="${credBad ? 'bad' : ''}">${esc(r.credential)}</span></div>
        ${finding[r.id] ? `<div class="rf">${ICON.warn}${esc(finding[r.id])}</div>` : ''}</div>`;
    }).join('')}</div>`);
  }
  if (p.summary) {
    const x = p.summary;
    out.push(`<div class="card brand"><div class="t">${ICON.identity}${x.agents} agents found · ${x.owned} of ${x.agents} now owned · ${x.shared_logins} on a person's login</div><div class="xs">${esc(p.note || '')}</div></div>`);
  }
  return out.join('');
}

function panelOnboard(s, p) {
  const rows = p.rows || [];
  const out = [pHead(s, 'Mediate, don’t modify', 'All four are taken over without changing their code: the controls attach to the credential, the path and the data.')];
  if (p.guardrails) {
    out.push(`<div class="li done">${okTag(true, `${rows.filter((r) => r.done).length} of 4 onboarded`)}<span>code unchanged · every call now passes the plane</span></div>`);
    out.push(`<h4 class="sec-t">Day zero: the plane holds only what people wrote</h4><div class="guard">${p.guardrails.map((g) => `<div class="g">${ICON.lock}<span><b>${esc(g.text)}</b><code class="tid">${esc(g.rule)}@v${g.version}</code></span></div>`).join('')}</div>`);
    out.push(`<div class="card info">${ICON.info}<span>Default deny: <b>not yet</b>. Everything else is observed, not decided, until the owners sign a rulebook.</span></div>`);
    return out.join('');
  }
  out.push(`<div class="rows">${rows.map((r) => `<div class="row onb${r.done ? ' done' : ''}${p.current === r.agent ? ' current' : ''}">
    <div class="rn"><b>${esc(agentName(r.agent))}</b>${r.done ? okTag(true, 'onboarded') : '<span class="tag tag-info">waiting</span>'}</div>
    <div class="swap"><span class="before">${esc(r.before)}</span>${r.after ? `<span class="arrow">→</span><span class="after">${esc(r.after)}</span>` : ''}</div>
    ${r.done ? `<div class="xs dim">${esc(r.swap)} · attribution ${esc(String(r.attribution).toLowerCase())}</div>` : ''}</div>`).join('')}</div>`);
  return out.join('');
}

function panelShadow(s, p) {
  const t = p.totals || {};
  const out = [pHead(s, 'Watched, not blocked', 'A recorded week for all four agents, decided by the engine with enforcement off.')];
  const pct = p.total ? (100 * p.processed / p.total).toFixed(1) : 0;
  const qe = (p.calendar || []).find((c) => c.tag);
  if (p.findings) {
    out.push(`<div class="li sum"><b>${n0(t.observed || 0)}</b> calls watched · ${tag('would_deny', `${t.would_deny || 0} would stop`)}${tag('would_hold', `${t.would_hold || 0} would wait`)}${qe ? `<span class="tag tag-brand">${ICON.book}${esc(qe.dow)} ${esc(qe.date.slice(5))}: quarter-end</span>` : ''}</div>`);
  } else {
    out.push(`<div class="hero"><b>${n0(t.observed || 0)}</b><span>recorded calls replayed${p.running ? ` · ${n0(p.processed)} of ${n0(p.total)}` : ''}</span><div class="bar"><span style="width:${pct}%"></span></div></div>`);
    out.push(`<div class="stats3">${stat(n0(t.would_deny || 0), `${ICON.eye} would stop`, 'deny')}${stat(n0(t.would_hold || 0), `${ICON.hold} would wait for a person`, 'hold')}${stat(qe ? esc(qe.dow) : '—', qe ? `quarter-end day (${esc(qe.date.slice(5))})` : 'no calendar day', 'brand')}</div>`);
  }
  if (p.findings) {
    out.push(`<h4 class="sec-t">What the engine found</h4><div class="rows">${p.findings.map((f) => {
      const lead = f.kind === 'deny' ? `<span class="tag tag-deny">${ICON.warn}breaks ${esc(f.rule)}</span>` : f.kind === 'protect'
        ? `<span class="tag tag-brand">${ICON.lock}rare but required</span>` : `<span class="tag tag-hold">${ICON.hold}needs a checker</span>`;
      return `<div class="row f-${f.kind}${f.kind === 'deny' ? ' hl' : ''}"><div class="rn">${lead}<b>${esc(short(f.agent))}</b></div>${what(f.capability)}<div class="xs">${esc(f.text)}</div></div>`;
    }).join('')}</div>`);
  } else {
    out.push('<p class="note">On the map, every line is one agent reaching one system; thicker means used more this week.</p>');
  }
  return out.join('');
}

function lineGroups(p) {
  const verdict = Object.fromEntries((p.verdicts || []).map((v) => [v.n, v]));
  const g = {};
  for (const l of p.lines || []) {
    const k = l.kind === 'grant' ? l.agent : l.kind;
    (g[k] = g[k] || []).push({ ...l, v: verdict[l.n] });
  }
  return g;
}

function panelRulebook(s, p) {
  const st = p.stage;
  const g = lineGroups(p);
  const verifying = ['verify', 'replay', 'approved'].includes(st) || !!p.verified;
  const model = p.model ? aiTag(`${modelName(p.model)}${p.latency_ms ? ` · ${secs(p.latency_ms)}` : ''}`) : '';
  const titles = { draft: 'AI drafts the rulebook', verify: 'A verifier checks every line', replay: 'Replayed against the week',
    approved: p.default_deny ? 'Signed, so enforced' : 'The owners sign' };
  const subs = { draft: 'From what the engine recorded. It is data: the AI cannot grant anything.',
    verify: 'Deterministic: backed by use or a declared purpose, no guardrail broken, restricted data purpose-bound.',
    replay: 'Every recorded call against the signed-to-be rulebook, with default deny on.',
    approved: 'People sign for every entitlement. AI never approves.' };
  const out = [pHead(s, titles[st] || 'The rulebook', subs[st] || '', st === 'draft' ? model : '')];
  const late = st === 'replay' || st === 'approved';
  if (!late) {
    const rows = AGENTS.filter((a) => g[a]).map((a) => {
      const ls = g[a];
      const done = ls.filter((x) => x.v);
      const bad = done.filter((x) => !x.v.ok);
      const verdict = !verifying ? `<span class="xs aitext">${plural(ls.length, 'grant')} proposed</span>`
        : done.length < ls.length ? `<span class="xs dim">checking ${done.length} of ${ls.length}…</span>`
          : bad.length ? `${okTag(false, `${ls.length - bad.length} of ${ls.length}`)}<span class="xs bad">${esc(bad[0].v.reason)}</span>` : okTag(true, `${ls.length} of ${ls.length} verified`);
      return `<div class="row"><div class="rn"><b>${esc(agentName(a))}</b>${verdict}</div><div class="caps">${ls.map((x) => `<span class="cap${x.v ? (x.v.ok ? ' ok' : ' no') : ''}">${esc(plain(x.capability))}</span>`).join('')}</div></div>`;
    }).join('');
    const lo = g.left_out || [];
    const fl = (g.flag || []).concat(g.habit || []);
    const miss = g.missing || [];
    out.push(`<div class="card ai"><div class="ai-l">${ICON.ai}Drafted by the AI investigator · advisory</div><div class="rows">${rows}
      ${lo.length ? `<div class="row"><div class="rn"><b>Left out</b><span class="xs">${plural(lo.length, 'old entitlement')} never used</span></div></div>` : ''}</div></div>`);
    for (const x of fl) out.push(`<div class="card hold">${signTag('owner decision needed')}<div>${what(x.capability)}<span class="xs">${esc(short(x.agent))} · ${esc(x.v ? x.v.reason : x.kind === 'habit' ? 'found by the engine' : 'flagged by the AI')}</span></div></div>`);
    for (const x of miss.slice(0, 2)) out.push(`<div class="card deny">${okTag(false, 'missed by the draft')}<div>${what(x.capability)}<span class="xs">${esc(short(x.agent))} · ${esc(x.v ? x.v.reason : '')}</span></div></div>`);
  } else {
    const v = p.verified || {};
    out.push(`<div class="li">${okTag(!v.problems, `${v.ok} of ${v.total} grants verified`)}<span class="xs">${v.problems ? `${plural(v.problems, 'line')} the verifier would not accept` : 'every line backed by use or a declared purpose'} · <button class="link" data-cmd="lines">all lines</button></span></div>`);
  }
  if (p.replay) {
    const r = p.replay;
    out.push(`<div class="stats3">${stat(r.running ? '…' : `${n0(r.legit_broken)}<small> of ${n0(r.legit_total)}</small>`, 'legitimate calls broken', r.running ? '' : r.legit_broken ? 'deny' : 'allow')}
      ${stat(r.running ? '…' : `${r.violations_stopped}<small> of ${r.violations}</small>`, 'guardrail breaches stopped', r.running ? '' : r.violations_stopped === r.violations ? 'allow' : 'deny')}
      ${stat(r.running ? '…' : r.held, 'held for a checker', 'hold')}</div>`);
  }
  if (p.version) {
    out.push(`<div class="card brand">${ICON.sign}<div><b class="mono">${esc(p.version.before)} → ${esc(p.version.after)}</b><span class="xs">Signed by the agents’ owners (${esc(p.version.how)}). The AI drafted it; it could not sign it.</span></div></div>`);
    for (const d of p.decisions || []) {
      out.push(`<div class="card deny">${tag('deny', 'rejected by the owner')}<div>${what(d.capability)}<span class="xs">${esc(short(d.agent))} · ${esc(d.pattern || `${d.observed}×`)} · decided by ${esc(d.by)}, not by the AI</span></div></div>`);
    }
  }
  if (p.default_deny) out.push(`<div class="card enforce">${ICON.lock}<b>Default deny is on.</b><span class="xs">Only what the signed rulebook allows now runs.</span></div>`);
  if (st === 'draft' || st === 'verify') out.push(`<button class="link more" data-cmd="lines">${ICON.list}All ${(p.lines || []).length} lines</button>`);
  return out.join('');
}

function panelEnforce(s, p) {
  const routine = p.routine || [];
  const out = [pHead(s, p.need ? 'Two minutes of exactly what it needs' : 'Normal work flows', p.need ? 'Just-in-time access: an exception inside a pre-approved envelope, then it expires.' : 'Default deny is on. Every call cites its rule. No AI is in the decision.')];
  const allowed = routine.filter((r) => r.decision === 'allow').length;
  const fast = routine.length ? Math.max(...routine.map((r) => r.ms || 0)) : null;
  out.push(`<div class="stats3">${stat(`${allowed}<small> of ${routine.length}</small>`, 'routine calls allowed', 'allow')}${stat(fast != null ? fast.toFixed(3) : '—', 'slowest decision (ms)', 'brand')}${stat('0', 'model calls in the path')}</div>`);
  if (p.need) out.push(`<div class="li">${ICON.jit}<span><b>Break ${esc(p.need.break)}</b> needs the legal entity ID from ${esc(p.need.system)}. ${esc(p.need.why)}</span></div>`);
  if (p.envelope) {
    const e = p.envelope;
    out.push(`<div class="card ${e.status === 'active' ? 'allow' : 'deny'} env"><div class="countdown2"><b>${e.remaining}</b><span>seconds left · demo clock</span></div>
      <div><b>${e.status === 'active' ? 'Granted' : 'Expired'}: one client, three fields, read-only</b><span class="xs">${esc(e.counterparty)} · ${e.fields.map(esc).join(', ')} · envelope <code>${esc(e.id)}</code></span></div></div>`);
  }
  if (p.jit_read) out.push(`<div class="li">${tag(p.jit_read.decision)}<span>Read within the envelope; tax ID, email and date of birth stay masked <code class="tid">${esc(p.jit_read.rule)}</code></span></div>`);
  if (p.after) out.push(`<div class="li">${tag(p.after.decision)}<span>The same read after expiry: ${esc(p.after.reason)} <code class="tid">${esc(p.after.rule)}</code></span></div>`);
  return out.join('');
}

function highlightNote(text, injected) {
  const i = text.indexOf(injected);
  if (i < 0) return esc(text);
  return `${esc(text.slice(0, i))}<mark class="inj">${esc(injected)}</mark>${esc(text.slice(i + injected.length))}`;
}

function stepPlain(x) {
  if (x.tool === 'agent.ask') return `Ask the settlement agent: ${plain(x.capability).toLowerCase()}`;
  return plain(x.capability);
}

function panelAttack(s, p) {
  const st = p.stage;
  const titles = { note: 'A hidden instruction', plan: 'The live model plans to follow it', today: 'Today: nothing stops it',
    governed: 'Same plan, through the control plane', case: 'The model was fooled. The system held.' };
  const subs = { note: 'In a settlement note the reconciliation agent reads. Untrusted content.',
    plan: 'The agent’s plan is AI output: the model decides what to try, never what is allowed.',
    today: 'Simulated: the same plan with nothing in the path.', governed: 'Every call is decided by rule. The model is allowed to fail.',
    case: 'AI explains. Pre-agreed rules decide what happens next.' };
  const out = [pHead(s, titles[st] || 'Catching a rogue agent', subs[st] || '')];
  if (p.note && st === 'note') {
    out.push(`<div class="card note"><div class="xs dim">${esc(p.note.source)} · ${esc(p.note.trade_id)}</div><div class="note-text">${highlightNote(p.note.text, p.note.injected)}</div></div>`);
  }
  if (p.fallback && (st === 'plan' || st === 'today')) out.push(`<div class="card sim">${simTag('recorded plan')}<span class="xs">${esc(p.fallback)}</span></div>`);
  if (p.plan && st === 'plan') {
    const label = p.plan_source === 'recorded' ? simTag('recorded plan') : aiTag(`live plan · ${modelName(p.model) || s.models.agent || ''}`);
    out.push(`<div class="card ai">${label}<ol class="plan">${p.plan.map((x) => `<li class="${x.harmful ? 'harm' : ''}"><span class="n">${x.n}</span><span>${esc(stepPlain(x))}<code class="tid">${esc(x.tool)} ${esc(x.args)}</code></span></li>`).join('')}</ol></div>`);
  }
  if (p.today && st === 'today') {
    out.push(`<div class="rows">${p.today.steps.map((r) => `<div class="row ${r.harmful ? 'hl' : ''}"><div class="rn"><span class="tag ${r.harmful ? 'tag-deny' : 'tag-sim'}">${ICON.warn}unchecked</span><b>${esc(stepPlain({ ...r, tool: r.chain.length > 1 ? 'agent.ask' : '' }))}</b></div><div class="xs ${r.harmful ? 'bad' : 'dim'}">${esc(r.outcome)}</div></div>`).join('')}</div>`);
    if (p.today.outcome) out.push(`<div class="card deny big">${ICON.warn}<b>${esc(p.today.outcome)}</b></div>`);
  }
  if (st === 'governed' || st === 'case') {
    const g = p.governed || [];
    if (st === 'governed') {
      out.push(`<div class="rows">${g.map((r) => `<div class="row d-${r.decision}"><div class="rn">${tag(r.decision)}<b>${esc(stepPlain({ ...r, tool: r.chain.length > 1 ? 'agent.ask' : '' }))}</b></div><div class="xs">${esc(rulePlain(r.rule))} <code class="tid">${esc(r.rule)}</code></div></div>`).join('')}</div>`);
      if (p.intersection) {
        const x = p.intersection;
        const row = x.rows.find((r) => r.capability === x.requested) || {};
        const yn = (v) => (v ? '✓' : '✗');
        out.push(`<div class="card brand">${ICON.route}<div><b>Agent to agent: asking never adds authority</b><span class="xs">${esc(plain(x.requested))}: caller ${yn(row.caller)} ∩ callee ${yn(row.callee)} ∩ task ${yn(row.task)} ∩ policy ${yn(row.policy)} = ${esc(x.result)}</span></div></div>`);
      }
    } else {
      const denied = g.filter((r) => r.decision !== 'allow').length;
      out.push(`<div class="li">${tag('deny', `${denied} stopped`)}${tag('allow', `${g.length - denied} allowed`)}<span class="xs">each citing its rule</span></div>`);
    }
  }
  if (p.case) {
    const c = p.case;
    out.push(`<div class="card ai">${aiTag(`investigator · ${modelName(c.model)}${c.latency_ms ? ` · ${secs(c.latency_ms)}` : ''}`)}<b>${esc(c.id)} · ${esc(c.title)}</b><span class="small">${esc(c.narrative)}</span><span class="xs">Suspected cause: <b>${esc(String(c.cause).replace('_', ' '))}</b></span></div>`);
  }
  if (p.containment) {
    const c = p.containment;
    out.push(`<div class="card deny"><b>${ICON.lock}Session ${esc(c.action.replace('_', '-'))} by rule <code>${esc(c.playbook)}</code></b><span class="xs">The AI recommended ${esc(c.recommended || 'nothing')}: ${esc(c.recommendation)}. Owner notified: ${esc(c.owner_notified)}.</span></div>`);
  }
  return out.join('');
}

function changePlain(c) {
  let params = {};
  try { params = c.params ? JSON.parse(c.params) : {}; } catch (e) { params = {}; }
  if (c.op === 'restrict_delegation') return `${agentName(c.agent)} may no longer ask ${agentName(c.target)} for client data`;
  if (c.op === 'require_human_for_envelope') return `A person approves the two-minute Client master access for ${params.days || 'some'} days`;
  if (c.op === 'remove_grant') return `Remove “${plain(c.target)}” from ${agentName(c.agent)}`;
  if (c.op === 'add_condition') return `Add a condition to “${plain(c.target)}”`;
  return `${c.op} ${c.target}`;
}

function panelHarden(s, p) {
  const st = p.stage;
  const titles = { draft: 'AI suggests tighter rules', replay: 'Replayed: week and attacks', approved: 'The owner signs', rerun: 'Tighter, and nothing broke' };
  const out = [pHead(s, titles[st] || 'Tighten', 'After the incident: AI drafts, a verifier checks, a person signs.',
    st === 'draft' && p.model ? aiTag(`${modelName(p.model)}${p.latency_ms ? ` · ${secs(p.latency_ms)}` : ''}`) : '')];
  const checks = p.checks || [];
  const later = ['approved', 'rerun'].includes(st);
  out.push(`<div class="card ai"><div class="ai-l">${ICON.ai}Proposed by the AI investigator · checked by the verifier</div><div class="rows">${(p.proposed || []).map((c, i) => {
    const v = checks[i];
    return `<div class="row"><div class="rn">${v ? okTag(v.ok, v.ok ? 'accepted' : 'rejected') : '<span class="tag tag-info">checking…</span>'}<b>${esc(changePlain(c))}</b></div>${later ? '' : `<code class="tid">${esc(c.op)} ${esc(c.target)} ${esc(c.params || '')}</code>`}${v && !v.ok ? `<span class="xs bad">${esc(v.reason)}</span>` : ''}</div>`;
  }).join('')}</div></div>`);
  if (p.replay && st === 'rerun') {
    const r = p.replay;
    out.push(`<div class="li">${okTag(!r.legit_broken, `${n0(r.legit_broken)} of ${n0(r.legit_total)} legitimate calls broken`)}${okTag(r.attacks_blocked === r.attacks_total, `${r.attacks_blocked} of ${r.attacks_total} attacks blocked`)}</div>`);
  } else if (p.replay) {
    const r = p.replay;
    out.push(`<div class="stats3">${stat(r.running ? '…' : `${n0(r.legit_broken)}<small> of ${n0(r.legit_total)}</small>`, `legitimate calls broken${r.quarter_end_ok ? ' · quarter-end intact' : ''}`, r.running ? '' : r.legit_broken ? 'deny' : 'allow')}
      ${stat(`${r.attacks_blocked}<small> of ${r.attacks_total}</small>`, 'attacks blocked in the suite', r.running ? '' : r.attacks_blocked === r.attacks_total ? 'allow' : 'deny')}</div>`);
  }
  if (p.approval && p.approval.skipped) out.push(`<div class="card info">${esc(p.approval.text)}</div>`);
  if (p.version) out.push(`<div class="card brand">${ICON.sign}<div><b class="mono">${esc(p.version.before)} → ${esc(p.version.after)}</b><span class="xs">Signed by the owner (${esc(p.version.how)}). The AI drafted it; it could not apply it.</span></div></div>`);
  if (p.rerun) {
    const r = p.rerun;
    const ran = (r.rows || []).filter((x) => x.decision !== 'not attempted');
    const skipped = (r.rows || []).length - ran.length;
    out.push(`<div class="card focus"><b>The same attack, again</b>${r.running ? '<span class="xs dim">running…</span>'
      : r.stopped_at ? `<span class="small">Stopped at step ${r.stopped_at} of ${r.total}: ${plural(r.attempted, 'call')} attempted (first time: ${r.act4_attempted}). Rule <code>${esc(r.playbook)}</code> revoked the session in ${ms(r.containment_ms)}.</span>`
        : `<span class="small">${plural(r.attempted, 'call')} attempted.</span>`}
      <div class="chips">${ran.map((x) => tag(x.decision, `${x.n} ${plain(x.capability)}`)).join('')}${skipped ? `<span class="tag tag-info">${plural(skipped, 'step')} never ran</span>` : ''}</div></div>`);
  }
  return out.join('');
}

function panelEvidence(s, p) {
  const m = p.metrics;
  if (!m) return pHead(s, 'Measured, not claimed', 'Evidence and optimisation.');
  const pct = m.consequential ? Math.round((100 * m.through_plane) / m.consequential) : 0;
  const tiles = [
    [`${m.through_plane}<small> of ${m.consequential}</small>`, 'calls through the plane', `${pct}% of governed agent calls`],
    [`${m.p50_ms}<small> / ${m.p95_ms} ms</small>`, 'decision time p50 / p95', 'in-process; target under 5 ms at the gateway'],
    [`${m.rulebook_ok}<small> of ${m.rulebook_total}</small>`, 'AI-drafted grants verified', `${n0(m.shadow_calls)} calls watched · ${m.guardrail_violations} breaches · ${plural(m.owner_rejected, 'habit')} rejected by its owner`],
    [`${m.attacks_blocked}<small> / ${m.attacks_total}</small>`, 'attacks blocked', `against ${esc(p.policy || '')}`],
    [`${n0(m.legit_broken)}<small> of ${n0(m.legit_total)}</small>`, 'legitimate calls broken', m.quarter_end_ok ? 'quarter-end intact' : 'quarter-end flow broken'],
    [m.containment_s != null ? `${m.containment_s}<small> s</small>` : '—', 'first malicious call to containment', `includes demo pacing · repeat ${ms(m.rerun_containment_ms)}`],
  ];
  const out = [pHead(s, 'Measured, not claimed', 'Every number here was measured in this run.', m.plan_source === 'recorded' ? simTag('agent plan: recorded') : aiTag('agent plan: live'))];
  out.push(`<div class="evgrid">${tiles.map(([b, l, d]) => `<div class="ev"><b>${b}</b><span class="l">${esc(l)}</span><span class="d">${d}</span></div>`).join('')}</div>`);
  out.push(`<div class="card deep">${m.chain_ok ? ICON.allow : ICON.deny}<div><b>Hash chain ${m.chain_ok ? 'verified' : 'BROKEN'}: ${n0(m.decisions)} decision records</b><span class="xs">${m.agents_owned} of ${m.agents_total} agents with an identity and owner (${m.workload_only} at workload level) · head <span class="mono">${esc((m.chain_head || '').slice(0, 16))}</span> · altering any record breaks the chain</span></div></div>`);
  if (!REPLAY && !ui.kv && !ui.rp) {
    out.push(`<div class="downloads"><a class="btn btn-quiet" href="/api/evidence.md" download>Evidence pack (.md)</a><a class="btn btn-quiet" href="/api/evidence.json" download>(.json)</a>${s.closed ? '<a class="btn btn-quiet" href="/api/keyviews/export" download>Download key views</a>' : ''}${p.close && ui.closeHidden ? '<button class="btn btn-quiet" data-cmd="close-show">Close card</button>' : ''}</div>`);
  }
  return out.join('');
}

function panelExtra(s, p) {
  const out = [pHead(s, 'Not every rogue agent is an attacker', 'A malfunction: a loop, caught by a volume rule.', p.quarantined ? `<span class="tag tag-deny">${ICON.lock}quarantined</span>` : `<span class="tag tag-hold">${ICON.hold}looping</span>`)];
  out.push(`<div class="stats3">${stat(p.held || 0, `${ICON.hold} settlement changes held`, 'hold')}${stat(p.ratio ? `${p.ratio}×` : '—', 'volume vs baseline', 'deny')}${stat(p.quarantined ? 'yes' : 'no', 'quarantined', p.quarantined ? 'deny' : '')}</div>`);
  if (p.monitor) out.push(`<div class="card info">${esc(p.monitor)} → rule <code>R-VOL-01</code> (over 10× in 60 s quarantines).</div>`);
  if (p.paged) out.push(`<div class="card brand">${ICON.lock}<div><b>Quarantine by ${esc(p.playbook)} · owner paged: ${esc(p.paged)}</b><span class="xs">Every looping copy waited for a checker (<code>R-SSI-01</code>); nothing was changed.</span></div></div>`);
  return out.join('');
}

// --- above the act panel: waiting, paused, a failed model call, an owner's signature ---
// These never touch the caption row or the layout: they float over the act panel.

function switchOptions(role) {
  const opts = (ui.conn && ui.conn.switch && ui.conn.switch[role]) || [];
  return opts.map((o) => `<option value="${esc(o.ref)}" ${ui.switchPick === o.ref ? 'selected' : ''}>${esc(o.name)}${o.tested ? ' · tested ✓' : ' · tested live first'}</option>`).join('');
}

function renderPanelOver(s) {
  if (ui.kv) return '';
  const e = ui.rp ? null : s.error;
  if (e && e.message) {
    const role = e.role || 'investigator';
    const ctl = !REPLAY && !viewer();
    const opts = switchOptions(role);
    return `<div class="over card-err" role="alertdialog" aria-label="Paused: a model call failed">
      <span class="eyebrow bad">${ICON.warn}Paused · the ${esc(e.label || e.job || role)} call failed</span>
      <h3>${esc(e.message)}</h3>
      <p class="xs">Needed at <b>${esc(e.needed_at || mmss(s.t))}</b> · ${esc(role)} model <b>${esc(e.model_name || s.models[role] || '')}</b>. Nothing was invented: the demo waits for a real result.</p>
      ${e.need_token && ctl ? `<div class="row2"><input id="tok-new" type="password" autocomplete="off" spellcheck="false" placeholder="Paste a fresh token"><button class="btn btn-primary" data-cmd="token-submit">Use token and retry</button></div>` : ''}
      ${ctl ? `<div class="actions">
        ${e.need_token ? '' : `<button class="btn btn-primary" data-cmd="retry" ${ui.busy ? 'disabled' : ''}>${ICON.restart}Retry this call</button>`}
        ${e.kind === 'timeout' ? '<button class="btn btn-quiet" data-cmd="wait">Keep waiting</button>' : ''}
        ${opts ? `<span class="sw"><select id="sw-model" aria-label="Switch ${esc(role)} model">${opts}</select><button class="btn btn-quiet" data-cmd="switch:${role}" ${ui.busy ? 'disabled' : ''}>Switch ${esc(role)} model</button></span>` : ''}
        <button class="btn btn-quiet" data-cmd="restart">Restart</button></div>
        ${ui.switchMsg ? `<p class="xs bad">${esc(ui.switchMsg)}</p>` : ''}` : '<p class="xs dim">This tab is a viewer.</p>'}
    </div>`;
  }
  if (s.approval) {
    const ap = s.approval;
    const btn = `<button class="btn btn-primary" data-cmd="approve" ${REPLAY || ui.rp || viewer() ? 'disabled' : ''}>${ICON.sign}${ap.kind === 'rulebook' ? 'Sign the rulebook, reject the export' : 'Sign'}</button>`;
    const body = ap.kind === 'rulebook'
      ? `<div class="rows">${(ap.items || []).map((i) => `<div class="li">${tag('allow', plural(i.grants, 'grant'))}<span><b>${esc(agentName(i.agent))}</b> · signed by ${esc(i.owner || '')}</span></div>`).join('')}
         ${(ap.reject || []).map((r) => `<div class="li">${tag('deny', 'reject')}<span><b>${esc(plain(r.capability))}</b> · ${esc(short(r.agent))} · ${esc(r.pattern || `${r.observed}×`)} · decided by ${esc(r.owner)}</span></div>`).join('')}</div>
         <p class="xs dim">Replay: ${n0(ap.replay)} legitimate calls broken. ${esc(ap.before)} → ${esc(ap.after)}, then default deny switches on.</p>`
      : `<p class="small">Apply ${plural(ap.changes, 'verified change')}: <span class="mono">${esc(ap.before)} → ${esc(ap.after)}</span>. Replay: ${n0(ap.replay)} legitimate calls broken.</p>`;
    return `<div class="over card-sign" role="dialog" aria-label="Owner signature"><span class="eyebrow">${ICON.person}Waits for a person</span><h3>${esc(ap.title)}</h3>${body}
      <div class="countdown"><b>${ap.remaining}</b><span>Auto-signs when the countdown ends, labelled “auto-signed for demo”. In production nothing auto-approves.</span></div>
      <div class="actions">${btn}</div></div>`;
  }
  if (ui.rp) return '';
  if (s.waiting) {
    const job = s.waiting.job;
    return `<div class="over card-wait"><span class="eyebrow aitext">${ICON.ai}<span class="pulse">Waiting for the ${esc(s.waiting.role)} model</span></span>
      <p class="small">The ${esc(JOB_SHORT[job] ? JOB_SHORT[job].toLowerCase() : job)} call is still in flight (${esc(s.models[s.waiting.role] || '')}). The clock is held; nothing is invented.</p></div>`;
  }
  if (s.paused && !REPLAY) {
    return `<div class="over card-pause"><span class="eyebrow">${ICON.pause}Paused by the presenter</span>${viewer() ? '' : '<p class="small">Press <span class="kbd">Space</span> or ▶ to continue.</p>'}</div>`;
  }
  return '';
}

// --- overlays: act intro, close card, drawers (decisions, a record, rulebook lines), key views ---

function drawerLog(s) {
  const rows = rowsFor(s).slice().reverse();
  const f = ui.filter;
  const list = rows.map((r) => {
    const who = r.chain && r.chain.length > 1 ? r.chain.map(short).join(' → ') : short(r.agent);
    const when = r.recorded_at ? `rec. ${r.recorded_at.slice(5, 10)}` : mmss(r.t);
    const t = r.kind === 'call' ? `<span class="tag ${r.harmful ? 'tag-deny' : 'tag-sim'}">${ICON.warn}unchecked</span>` : tag(r.decision);
    return `<button class="drow" data-cmd="record:${r.seq}"><span class="tt">${esc(when)}</span>${t}<span class="dw2"><b>${esc(who)}</b> · ${esc(plain(r.capability))}<code class="tid">${esc(r.capability)} → ${esc(r.resource || r.system || '')} · ${esc(r.kind === 'call' ? 'no control' : r.rule)}${r.elapsed_ms != null ? ` · ${ms(r.elapsed_ms)}` : ''}</code></span></button>`;
  }).join('');
  return `<header><b>${ICON.list}All decisions${f ? ` · ${esc(agentName(f.agent))}${f.system ? ` → ${esc(systemName(f.system))}` : ''}` : ''}</b><span class="xs dim">${n0(rows.length)} shown · newest first · click one for its full record</span>
    ${f ? '<button class="btn btn-quiet" data-cmd="filter-clear">Show all</button>' : ''}<button class="ibtn" data-cmd="drawer-close" title="Close (Esc)">${ICON.close}</button></header>
    <div class="scroll" tabindex="0" id="drawer-scroll">${list || '<p class="note">Nothing decided yet.</p>'}</div>`;
}

function drawerRecord(s, seq) {
  const row = s.timeline.find((r) => r.seq === seq);
  if (!row) return drawerLog(s);
  const rec = { ...row };
  delete rec.kind; delete rec.act;
  return `<header><b>${row.kind === 'call' ? 'Ungoverned call (today mode, simulated)' : `Decision record · ${esc(row.request_id)}`}</b>
    <button class="btn btn-quiet" data-cmd="log">${ICON.prev}All decisions</button><button class="ibtn" data-cmd="drawer-close" title="Close (Esc)">${ICON.close}</button></header>
    <div class="scroll" tabindex="0" id="drawer-scroll"><p class="small"><b>${esc(plain(row.capability))}</b> · ${esc(decisionWord(row))}${row.rule ? ` by ${esc(rulePlain(row.rule))} <code>${esc(row.rule)}@v${esc(row.rule_version)}</code>` : ''}</p><pre>${esc(JSON.stringify(rec, null, 2))}</pre></div>`;
}

function drawerLines(s) {
  const p = s.panels.rulebook || {};
  const verdict = Object.fromEntries((p.verdicts || []).map((v) => [v.n, v]));
  const kindWord = { grant: 'grant', flag: 'flag for the owner', left_out: 'left out', missing: 'missed by the draft', habit: 'habit found by the engine' };
  const list = (p.lines || []).map((l) => {
    const v = verdict[l.n];
    return `<div class="drow static"><span class="tt">${l.n}</span>${v ? okTag(v.ok, v.ok ? 'verified' : 'rejected') : '<span class="tag tag-ai">drafted</span>'}<span class="dw2"><b>${esc(short(l.agent))}</b> · ${esc(kindWord[l.kind] || l.kind)}: ${esc(plain(l.capability))}<code class="tid">${esc(l.capability)}${v ? ` · ${esc(v.reason)}` : ''}</code></span></div>`;
  }).join('');
  return `<header><b>${ICON.list}The rulebook, line by line</b><span class="xs dim">AI drafted · verifier checked</span><button class="ibtn" data-cmd="drawer-close" title="Close (Esc)">${ICON.close}</button></header>
    <div class="scroll" tabindex="0" id="drawer-scroll">${list || '<p class="note">No draft yet.</p>'}</div>`;
}

function renderOverlays(s) {
  const out = [];
  if (s.intro && !ui.kv) {
    out.push(`<div class="intro"><div class="intro-card"><span class="eyebrow">Act ${s.intro.act} of 6${s.intro.gist ? ` · ${esc(s.intro.gist)}` : ''}</span><h2>${esc(s.intro.title)}</h2><p>${esc(s.intro.sub || '')}</p>
      ${s.intro.deck ? `<span class="chip deck">${ICON.book}Deck: ${esc(s.intro.deck)}</span>` : ''}</div></div>`);
  }
  const ev = s.panels.evidence;
  if (ev && ev.close && !ui.closeHidden && !ui.kv) {
    out.push(`<div class="closewrap"><div class="closecard"><button class="ibtn x" data-cmd="close-hide" title="Hide">${ICON.close}</button>
      <span class="eyebrow">Synthetic estate · next step</span><h3>Run Acts 1–3 on a real slice of your estate</h3>
      <ol>${ev.close.asks.map((a) => `<li>${esc(a)}</li>`).join('')}</ol>
      <span class="motto">Policy decides. AI advises. People approve.</span>
      ${ui.rp ? '' : `<div class="downloads">${replayAvailable() ? '<button class="btn btn-primary" data-cmd="replay">' + ICON.play + 'Captioned replay <span class="kbd">P</span></button>' : ''}
      ${!REPLAY ? `<button class="btn ${replayAvailable() ? 'btn-quiet' : 'btn-primary'}" data-cmd="film">Key views <span class="kbd">K</span></button>` : ''}
      ${!REPLAY && s.done && !viewer() ? `<button class="btn btn-quiet" data-cmd="extra" ${s.extraDone ? 'disabled' : ''}>Extra: malfunction</button>` : ''}</div>`}</div></div>`);
  }
  if (ui.drawer) {
    const body = ui.drawer.kind === 'record' ? drawerRecord(s, ui.drawer.seq) : ui.drawer.kind === 'lines' ? drawerLines(s) : drawerLog(s);
    out.push(`<aside class="drawer" aria-label="Details">${body}</aside>`);
  }
  if (ui.film && ui.kvData) {
    const curI = ui.kv ? ui.kv.i : -1;
    out.push(`<div class="scrim" data-cmd="film-close"><div class="film"><div class="ph"><h3>Key views · recorded from this run · no live calls</h3><button class="ibtn" data-cmd="film-close">${ICON.close}</button></div>
      <div class="film-cards">${ui.kvData.views.map((v, i) => `<button class="kcard ${i === curI ? 'current' : ''}" style="--actc:${ACT_COLOR[v.act] || 'var(--brand)'}" data-cmd="kv-go:${i}"><span class="n">${v.n}</span><span class="ti">${esc(v.title)}</span><span class="ca">${esc(v.caption)}</span></button>`).join('')}</div>
      <div class="downloads">${ui.kvData.replay ? `<button class="btn btn-primary" data-cmd="replay">${ICON.play}Captioned replay · ${mmss(ui.kvData.replay.total)}</button>` : ''}${REPLAY ? '' : '<a class="btn btn-quiet" href="/api/keyviews/export" download>Download key views and replay</a>'}</div></div></div>`);
  }
  return out.join('');
}

// ---------------------------------------------------------------------------------------------
// Key views: fold the recorded log up to the k-th marker
// ---------------------------------------------------------------------------------------------

function enterKeyView(i) {
  const views = ui.kvData.views;
  i = Math.max(0, Math.min(views.length - 1, i));
  const upto = views[i].seq;
  const state = fold(ui.kvData.events.filter((e) => e.seq <= upto));
  state.intro = null; state.approval = null; state.waiting = null; state.error = null; state.paused = false;
  stopReplay();
  ui.kv = { i, state };
  ui.film = false;
  ui.drawer = null;
  schedule();
}

async function openKeyViews() {
  if (!ui.kvData) {
    if (REPLAY) return;
    try { ui.kvData = await api('GET', '/api/keyviews'); } catch (e) { return; }
  }
  ui.film = true;
  schedule();
}

function exitKeyViews() { ui.kv = null; ui.film = false; ui.drawer = null; schedule(); }

// ---------------------------------------------------------------------------------------------
// Captioned replay (SPEC §5.9): the run's own log, re-folded on a compressed clock with callouts.
// Playback only: no server calls, no decisions, no model. Section speeds and callout texts come from
// app/demo/replay.py with the key-view data (and inside the exported file).
// ---------------------------------------------------------------------------------------------

function replayAvailable() {
  if (REPLAY) return !!(ui.kvData && ui.kvData.replay);
  return !!((ui.kvData && ui.kvData.replay) || (ui.conn && ui.conn.keyviews) || cur().closed);
}

const keepInReplay = (e) => e.kind !== 'error' && !(e.kind === 'system' && ('paused' in e.payload || 'waiting' in e.payload));

function warpT(t) {
  let r = 0;
  for (const [a, b, sec] of ui.rp.warp) {
    if (t >= b) r += sec;
    else if (t > a) return r + ((t - a) / (b - a)) * sec;
    else break;
  }
  return r;
}

async function openReplay(play) {
  if (!REPLAY && !(ui.kvData && ui.kvData.replay)) {
    try { ui.kvData = await api('GET', '/api/keyviews'); } catch (e) { return; }
  }
  const data = ui.kvData && ui.kvData.replay;
  if (!data) return;
  stopReplay();
  ui.kv = null; ui.film = false; ui.drawer = null; ui.filter = null;
  ui.rp = { warp: data.warp, total: data.total, callouts: data.callouts, meta: ui.kvData.meta || {},
    events: ui.kvData.events.filter(keepInReplay), pos: 0, playing: false, started: false, ended: false,
    i: 0, state: initialState(), base: 0, t0: 0, timer: 0, shown: -2 };
  for (const e of ui.rp.events) e.rt = warpT(e.t);
  seekReplay(0, play);
}

function seekReplay(pos, play) {
  const r = ui.rp;
  if (!r) return;
  r.pos = Math.max(0, Math.min(r.total, pos));
  const upto = r.events.filter((e) => e.rt <= r.pos + 1e-6);
  r.state = fold(upto);
  r.i = upto.length;
  ui.animSeq = r.state.lastSeq;              // a seek lands on a still frame; only new events animate
  r.ended = r.pos >= r.total;
  if (play && !r.ended) startReplay(); else if (r.playing) pauseReplay();
  schedule();
}

function startReplay() {
  const r = ui.rp;
  r.playing = true; r.started = true; r.ended = false;
  r.base = r.pos; r.t0 = performance.now();
  clearInterval(r.timer);
  r.timer = setInterval(tickReplay, 50);
  schedule();
}

function pauseReplay() {
  const r = ui.rp;
  r.playing = false; r.base = r.pos;
  clearInterval(r.timer);
  schedule();
}

function toggleReplay() {
  const r = ui.rp;
  if (!r) return;
  if (r.ended) seekReplay(0, true);
  else if (r.playing) pauseReplay();
  else startReplay();
}

function tickReplay() {
  const r = ui.rp;
  if (!r || !r.playing) return;
  r.pos = Math.min(r.total, r.base + (performance.now() - r.t0) / 1000);
  let changed = false;
  while (r.i < r.events.length && r.events[r.i].rt <= r.pos) { r.state = apply(r.state, r.events[r.i]); r.i += 1; changed = true; }
  if (r.pos >= r.total) { r.playing = false; r.ended = true; clearInterval(r.timer); changed = true; }
  if (changed || currentCallout() !== r.shown) schedule(); else updateReplayClock();
}

function stopReplay() {
  if (ui.rp) clearInterval(ui.rp.timer);
  ui.rp = null;
}

function exitReplay() {
  stopReplay();
  if (REPLAY && ui.kvData.views.length) enterKeyView(0); else schedule();
}

function currentCallout() {
  const r = ui.rp;
  if (!r || !r.started) return -1;
  return r.callouts.findIndex((c) => r.pos >= c.at_r && r.pos < c.at_r + c.show_r);
}

function stepCallout(dir) {
  const r = ui.rp;
  if (!r) return;
  const cs = r.callouts;
  const target = dir > 0 ? cs.find((c) => c.at_r > r.pos + 0.05) : [...cs].reverse().find((c) => c.at_r < r.pos - 1.2);
  r.started = true;
  seekReplay(target ? target.at_r + 0.01 : dir > 0 ? r.total : 0, r.playing);
}

function updateReplayClock() {
  const r = ui.rp;
  const b = $('#rp-time b');
  if (b) { const t = mmss(r.pos); if (b.textContent !== t) b.textContent = t; }
  const fill = $('#rp-fill');
  if (fill) fill.style.width = `${(100 * r.pos / r.total).toFixed(2)}%`;
}

function renderReplayLayer() {
  let layer = $('#rp-layer');
  if (!layer) { layer = document.createElement('div'); layer.id = 'rp-layer'; $('#console').appendChild(layer); }
  const r = ui.rp;
  if (!r) { if (layer.innerHTML) layer.innerHTML = ''; return; }
  const idx = currentCallout();
  const key = `${idx}|${r.started}|${r.ended}|${r.playing}|${document.documentElement.dataset.theme}`;
  if (layer.dataset.key !== key || !layer.innerHTML) {
    layer.dataset.key = key;
    r.shown = idx;
    const acts = [25, 80, 110, 140, 225].map((t) => `<i class="tick" style="left:${(100 * warpT(t) / r.total).toFixed(2)}%"></i>`).join('');
    const dots = r.callouts.map((c, i) => `<i class="cdot${i === idx ? ' on' : ''}" style="left:${(100 * c.at_r / r.total).toFixed(2)}%" title="${esc(c.title)}"></i>`).join('');
    const c = idx >= 0 ? r.callouts[idx] : null;
    const card = !r.started
      ? `<div class="rp-card"><span class="eyebrow">${ICON.play}Captioned replay · ${mmss(r.total)}</span><h3>The live run, in ${Math.round(r.total)} seconds</h3>
          <p>A recording of the run at ${esc(String(r.meta.recorded_at || '').slice(11, 16))} (models ${esc(modelName(r.meta.agent_model))} / ${esc(modelName(r.meta.investigator_model))}). It plays by itself; callouts explain each step. Nothing runs live and no model is called.</p>
          <div class="actions"><button class="btn btn-primary" data-cmd="rp-toggle">${ICON.play}Play <span class="kbd">Space</span></button><button class="btn btn-quiet" data-cmd="film">Key views</button></div></div>`
      : r.ended
        ? `<div class="rp-card"><span class="eyebrow">End of the replay</span><h3>Policy decides. AI advises. People approve.</h3>
            <div class="actions"><button class="btn btn-primary" data-cmd="rp-restart">${ICON.restart}Replay again</button><button class="btn btn-quiet" data-cmd="film">Key views</button><button class="btn btn-quiet" data-cmd="rp-exit">${REPLAY ? 'Stop' : 'Back'}</button></div></div>`
        : '';
    layer.innerHTML = `<div class="rp-bar" id="rp-bar" title="Click to jump"><i class="fill" id="rp-fill"></i>${acts}${dots}</div>
      ${c ? `<div class="spot" id="rp-spot"></div><div class="callout" id="rp-callout" role="status"><span class="ce">${idx + 1} / ${r.callouts.length} · ${esc(c.title)}</span><p>${esc(c.text)}</p></div>` : ''}
      ${card ? `<div class="rp-scrim">${card}</div>` : ''}`;
  }
  updateReplayClock();
  placeReplayLayer(idx >= 0 ? r.callouts[idx] : null);
}

// Put the bar under the header and the callout next to what it describes (presentation only).
function placeReplayLayer(c) {
  const top = $('.top');
  const bar = $('#rp-bar');
  if (top && bar) bar.style.top = `${top.getBoundingClientRect().bottom}px`;
  const box = $('#rp-callout'), spot = $('#rp-spot');
  if (!c || !box) return;
  let el = null;
  for (const sel of c.anchor) {
    const x = document.querySelector(`#console ${sel}`) || document.querySelector(sel);
    if (x && x.getBoundingClientRect().width > 0) { el = x; break; }
  }
  const a = (el || $('.panel-pane')).getBoundingClientRect();
  const vw = innerWidth, vh = innerHeight, pad = 6, gap = 14;
  const cap = $('.caption');
  const bottom = cap ? cap.getBoundingClientRect().top - 8 : vh - 8;
  const minTop = top ? top.getBoundingClientRect().bottom + 10 : 8;
  spot.style.cssText = `left:${a.left - pad}px;top:${a.top - pad}px;width:${a.width + 2 * pad}px;height:${a.height + 2 * pad}px`;
  const w = box.offsetWidth, h = box.offsetHeight;
  let side, x, y;
  if (a.right + gap + w <= vw - 8) { side = 'right'; x = a.right + gap; }
  else if (a.left - gap - w >= 8) { side = 'left'; x = a.left - gap - w; }
  else { side = 'inside'; x = Math.max(8, a.right - w - 12); }
  y = side === 'inside' ? a.top + 12 : a.top + Math.min(a.height, 160) / 2 - h / 2;
  y = Math.max(minTop, Math.min(bottom - h, y));
  box.dataset.side = side;
  box.style.left = `${x}px`; box.style.top = `${y}px`;
  const ay = Math.max(14, Math.min(h - 14, a.top + Math.min(a.height, 160) / 2 - y));
  box.style.setProperty('--ay', `${ay}px`);
}

document.addEventListener('click', (e) => {
  const bar = e.target.closest('#rp-bar');
  if (!bar || !ui.rp) return;
  const rect = bar.getBoundingClientRect();
  ui.rp.started = true;
  seekReplay(((e.clientX - rect.left) / rect.width) * ui.rp.total, ui.rp.playing);
});

// ---------------------------------------------------------------------------------------------
// Server calls (live mode only)
// ---------------------------------------------------------------------------------------------

async function api(method, url, body) {
  if (REPLAY) throw new Error('playback only');
  const headers = { 'X-Console-Id': CONSOLE_ID };
  if (body) headers['Content-Type'] = 'application/json';
  const r = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const err = new Error(data.detail || data.error || `HTTP ${r.status}`); err.status = r.status; throw err; }
  return data;
}

async function refreshConn() {
  try { ui.conn = await api('GET', '/api/connection/status'); } catch (e) { /* keep the last status */ }
  schedule();
}

async function control(cmd, value) {
  try { await api('POST', '/api/demo/control', { cmd, value }); } catch (e) {
    if (e.status === 409 && /Test the connection/.test(e.message)) showGate();
    if (e.status === 403) refreshConn();
  }
}

// The stream: a dropped connection (sleep, Wi-Fi) reconnects on its own and the server replays the run's
// log; events already folded are skipped by sequence number, so the console resyncs without a reload.
let source = null;
function connectStream() {
  if (source) source.close();
  source = new EventSource('/api/stream');
  source.onopen = () => { if (ui.stream === 'lost') refreshConn(); ui.stream = 'open'; schedule(); };
  source.onerror = () => { ui.stream = 'lost'; schedule(); };
  source.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.kind === 'run') {
      if (ev.run === ui.state.runId) return;                  // the same run, replayed after a reconnect
      ui.state = apply(initialState(), ev); ui.drawer = null; ui.closeHidden = false; ui.filter = null; ui.animSeq = 0;
      if (ui.kv) ui.kv = null;
      refreshConn();
    } else {
      if (ev.run !== ui.state.runId || ev.seq <= ui.state.lastSeq) return;
      ui.state = apply(ui.state, ev);
      if (ev.kind === 'error' || (ev.kind === 'system' && (ev.payload.closed || ev.payload.done || ev.payload.paused))) refreshConn();
      if (ev.kind === 'system' && (ev.payload.closed || ev.payload.done)) ui.kvData = null;
    }
    ui.clock = { seq: ui.state.lastSeq, at: performance.now() };
    schedule();
  };
}

// ---------------------------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------------------------

function toggleTheme() {
  const html = document.documentElement;
  const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
  html.dataset.theme = next;
  try { localStorage.setItem('agentgov-theme', next); } catch (e) { /* storage unavailable: theme still toggles */ }
  for (const k of Object.keys(cache)) delete cache[k];
  schedule();
}

function openDrawer(d) {
  ui.drawer = d;
  schedule();
  requestAnimationFrame(() => { const el = $('#drawer-scroll'); if (el) el.focus({ preventScroll: true }); });
}

async function onCommand(cmd) {
  const i = cmd.indexOf(':');
  const name = i < 0 ? cmd : cmd.slice(0, i);
  const arg = i < 0 ? '' : cmd.slice(i + 1);
  switch (name) {
    case 'pause': return control('pause');
    case 'resume': return control('resume');
    case 'next': return control('next');
    case 'restart': ui.kv = null; ui.film = false; ui.drawer = null; return control('restart');
    case 'speed': return control('speed', Number(arg));
    case 'jump': return control('jump', Number(arg));
    case 'theme': return toggleTheme();
    case 'film': return openKeyViews();
    case 'film-close': ui.film = false; return schedule();
    case 'kv-go': return enterKeyView(Number(arg));
    case 'kv-step': return ui.kv && enterKeyView(ui.kv.i + Number(arg));
    case 'kv-exit': return exitKeyViews();
    case 'replay': return openReplay(true);
    case 'rp-toggle': return toggleReplay();
    case 'rp-restart': return seekReplay(0, true);
    case 'rp-prev': return stepCallout(-1);
    case 'rp-next': return stepCallout(1);
    case 'rp-exit': return exitReplay();
    case 'log': return openDrawer({ kind: 'log' });
    case 'lines': return openDrawer({ kind: 'lines' });
    case 'record': return openDrawer({ kind: 'record', seq: Number(arg) });
    case 'drawer-close': ui.drawer = null; return schedule();
    case 'filter-agent': ui.filter = ui.filter && ui.filter.agent === arg && !ui.filter.system ? null : { agent: arg }; return schedule();
    case 'filter-edge': { const [a, sys] = arg.split('|'); ui.filter = ui.filter && ui.filter.agent === a && ui.filter.system === sys ? null : { agent: a, system: sys }; return schedule(); }
    case 'filter-clear': ui.filter = null; return schedule();
    case 'close-hide': ui.closeHidden = true; return schedule();
    case 'close-show': ui.closeHidden = false; return schedule();
    case 'approve': return api('POST', '/api/demo/approve').catch(() => refreshConn());
    case 'extra': ui.closeHidden = true; return api('POST', '/api/demo/extra').catch(() => {});
    case 'take-control': ui.conn = await api('POST', '/api/demo/take_control').catch(() => ui.conn); return schedule();
    case 'retry': return control('retry');
    case 'wait': return control('wait');
    case 'switch': {
      const sel = $('#sw-model');
      if (!sel || !sel.value) return undefined;
      ui.switchPick = sel.value; ui.busy = true; ui.switchMsg = ''; schedule();
      try { ui.conn = await api('POST', '/api/demo/switch_model', { role: arg, model: sel.value }); } catch (e) { ui.switchMsg = e.message; }
      ui.busy = false; return schedule();
    }
    case 'token-submit': {
      const el = $('#tok-new');
      const v = el ? el.value : '';
      if (!v.trim()) return undefined;
      el.value = '';
      try { await api('POST', '/api/connection/token', { token: v }); } catch (e) { ui.switchMsg = e.message; return schedule(); }
      ui.switchMsg = '';
      return control('retry');
    }
    default: return undefined;
  }
}

document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-cmd]');
  if (!el || el.disabled || !$('#console').contains(el)) return;
  if (el.classList.contains('scrim') && e.target !== el) return;     // clicks inside the filmstrip don't close it
  onCommand(el.dataset.cmd);
});

document.addEventListener('keydown', (e) => {
  if ($('#console').hidden || e.target.matches('input, select, textarea')) return;
  const s = ui.state;
  if (ui.rp && !ui.film && !ui.drawer) {
    const r = ui.rp;
    if (e.key === 'Escape') { e.preventDefault(); onCommand('rp-exit'); }
    else if (e.key === ' ') { e.preventDefault(); onCommand('rp-toggle'); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); onCommand('rp-next'); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); onCommand('rp-prev'); }
    else if (e.key === 'r' || e.key === 'R') onCommand('rp-restart');
    else if (e.key === 'k' || e.key === 'K') { e.preventDefault(); r.playing && onCommand('rp-toggle'); openKeyViews(); }
    else if (e.key === 'd' || e.key === 'D') toggleTheme();
    return;
  }
  if ((e.key === 'p' || e.key === 'P') && replayAvailable()) { e.preventDefault(); onCommand('replay'); return; }
  if (e.key === 'Escape') {
    if (ui.drawer) { ui.drawer = null; schedule(); } else if (ui.film) { ui.film = false; schedule(); } else if (ui.filter) { ui.filter = null; schedule(); } else if (ui.kv && !REPLAY) exitKeyViews();
    return;
  }
  if (e.key === 'k' || e.key === 'K') { e.preventDefault(); if (ui.film) { ui.film = false; schedule(); } else openKeyViews(); return; }
  if (e.key === 'd' || e.key === 'D') { toggleTheme(); return; }
  if (e.key === 'l' || e.key === 'L') { e.preventDefault(); if (ui.drawer) { ui.drawer = null; schedule(); } else openDrawer({ kind: 'log' }); return; }
  if (ui.drawer && ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End'].includes(e.key)) return;   // the drawer scrolls
  if (ui.kv) {
    if (e.key === 'ArrowRight') { e.preventDefault(); enterKeyView(ui.kv.i + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); enterKeyView(ui.kv.i - 1); }
    if ((e.key === 'r' || e.key === 'R') && !REPLAY && !viewer()) onCommand('restart');
    return;
  }
  if (REPLAY || viewer()) return;
  if (e.key === ' ') { e.preventDefault(); control(s.paused ? 'resume' : 'pause'); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); control('next'); }
  else if (e.key === 'r' || e.key === 'R') onCommand('restart');
});

window.addEventListener('resize', () => { delete cache['#map']; schedule(); });

// ---------------------------------------------------------------------------------------------
// Connection gate
// ---------------------------------------------------------------------------------------------

function modelOptions(provider, selected) {
  const list = provider === 'openrouter' ? ui.catalog.openrouter : ui.catalog.foundry;
  const known = list.some((m) => m.ref === selected);
  const opts = list.map((m) => `<option value="${esc(m.ref)}" ${m.ref === selected ? 'selected' : ''}>${esc(m.label)}${m.ref === ui.catalog.recommended[provider].agent || m.ref === ui.catalog.recommended[provider].investigator ? ' · recommended' : ''}</option>`);
  opts.push(`<option value="__custom" ${known ? '' : 'selected'}>Custom model id…</option>`);
  return opts.join('');
}

function gateModels() {
  const pick = (role) => {
    const sel = $(`#g-${role}`).value;
    return sel === '__custom' ? $(`#g-${role}-custom`).value.trim() : sel;
  };
  return { agent: pick('agent'), investigator: pick('investigator') };
}

function paintGate() {
  const c = ui.conn, g = ui.gate;
  for (const b of document.querySelectorAll('#g-provider button')) b.setAttribute('aria-checked', String(b.dataset.v === g.provider));
  $('#g-project-field').hidden = g.provider !== 'foundry';
  $('#g-masked').hidden = !c.token; $('#g-masked').textContent = c.token || '';
  $('#g-forget').hidden = !c.token;
  $('#g-token').placeholder = c.token ? 'Token held in memory: paste to replace' : 'Paste a fresh token';
  const rows = ['agent', 'investigator'].map((r) => {
    const t = c.tests[r];
    if (g.busy) return `<li><b>${r === 'agent' ? 'Agent' : 'Investigator'}</b><span class="msg pulse">testing ${esc(gateModels()[r])}…</span><span></span></li>`;
    if (!t) return '';
    return `<li><b>${r === 'agent' ? 'Agent' : 'Investigator'}</b><span class="msg">${okTag(t.ok, t.ok ? 'live' : 'failed')} ${esc(t.name)} · ${esc(t.message)}</span><span class="meta">${t.ok ? `${Math.round(t.latency_ms)} ms<br>${esc(t.variant)}` : ''}</span></li>`;
  }).join('');
  $('#g-results').innerHTML = rows;
  const pf = c.preflight;
  $('#g-preflight-results').innerHTML = g.preflight
    ? '<li><b>Preflight</b><span class="msg pulse">running the four real calls (rulebook, plan, case, hardening)…</span><span></span></li>'
    : pf ? pf.results.map((r) => `<li><b>${esc(JOB_SHORT[r.job])}</b><span class="msg">${okTag(r.ok, r.ok ? 'pass' : 'fail')} ${esc(r.model)} · ${esc(r.ok ? r.detail || 'valid JSON' : r.message)}</span><span class="meta">${r.latency_ms != null ? secs(r.latency_ms) : ''}</span></li>`).join('')
      + `<li class="pf-note"><span></span><span class="msg xs">Preflight from ${esc(hhmm(pf.at))}, this session only; not saved.</span><span></span></li>` : '';
  const active = c.run && c.run.active;
  $('#g-start').disabled = !c.ready || g.busy || g.starting || g.preflight;
  $('#g-start').textContent = active && c.controller && c.controller.set && !c.controller.you ? 'Watch the run' : 'Start demo';
  $('#g-test').disabled = g.busy || g.preflight;
  $('#g-preflight').disabled = !c.ready || g.busy || g.preflight;
}

function syncCustom(role) {
  const sel = $(`#g-${role}`);
  $(`#g-${role}-custom`).hidden = sel.value !== '__custom';
}

async function showGate() {
  if (source) { source.close(); source = null; }
  $('#console').hidden = true;
  $('#gate').hidden = false;
  if (!ui.catalog) ui.catalog = await api('GET', '/api/catalog');
  ui.conn = await api('GET', '/api/connection/status');
  ui.gate.provider = ui.conn.provider || 'foundry';
  const models = ui.conn.models || ui.catalog.recommended[ui.gate.provider];
  for (const role of ['agent', 'investigator']) {
    $(`#g-${role}`).innerHTML = modelOptions(ui.gate.provider, models[role]);
    if (!ui.catalog[ui.gate.provider === 'openrouter' ? 'openrouter' : 'foundry'].some((m) => m.ref === models[role])) $(`#g-${role}-custom`).value = models[role] || '';
    syncCustom(role);
  }
  $('#g-project').value = ui.conn.project || ui.catalog.defaults.project;
  $('#g-base').value = ui.conn.base_url || ui.catalog.defaults.base_url;
  $('#g-ca').value = ui.conn.ca_bundle || '';
  paintGate();
}

function gateError(where, e) {
  $('#g-results').insertAdjacentHTML('beforeend', `<li><b>${esc(where)}</b><span class="msg">${okTag(false, 'error')} ${esc(e.message)}</span><span></span></li>`);
}

function wireGate() {
  $('#g-provider').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-v]');
    if (!b || b.dataset.v === ui.gate.provider) return;
    ui.gate.provider = b.dataset.v;
    for (const role of ['agent', 'investigator']) { $(`#g-${role}`).innerHTML = modelOptions(ui.gate.provider, ui.catalog.recommended[ui.gate.provider][role]); syncCustom(role); }
    ui.conn.tests = {}; ui.conn.ready = false;
    paintGate();
  });
  for (const role of ['agent', 'investigator']) $(`#g-${role}`).addEventListener('change', () => { syncCustom(role); ui.conn.ready = false; paintGate(); });
  $('#g-forget').addEventListener('click', async () => { ui.conn = await api('POST', '/api/connection/forget'); paintGate(); });
  $('#g-test').addEventListener('click', async () => {
    // Only what the presenter pasted goes to the server; the masked display value never does.
    const token = $('#g-token').value;
    $('#g-token').value = '';
    ui.gate.busy = true; paintGate();
    try {
      ui.conn = await api('POST', '/api/connection/test', { provider: ui.gate.provider, token: token.trim() ? token : null, project: $('#g-project').value,
        models: gateModels(), base_url: $('#g-base').value, ca_bundle: $('#g-ca').value || null });
    } catch (e) {
      ui.gate.busy = false; paintGate(); gateError('Error', e); return;
    }
    ui.gate.busy = false; paintGate();
  });
  $('#g-preflight').addEventListener('click', async () => {
    ui.gate.preflight = true; paintGate();
    try { ui.conn = await api('POST', '/api/connection/preflight'); } catch (e) { ui.gate.preflight = false; paintGate(); gateError('Preflight', e); return; }
    ui.gate.preflight = false; paintGate();
  });
  $('#g-start').addEventListener('click', async () => {
    if (ui.gate.starting) return;                        // a double click is one start
    ui.gate.starting = true; paintGate();
    try {
      const c = ui.conn;
      if (!(c.run && c.run.active && c.controller && c.controller.set && !c.controller.you)) await api('POST', '/api/demo/start');
      await refreshConn();
      showConsole();
    } catch (e) { gateError('Start', e); refreshConn(); }
    ui.gate.starting = false; paintGate();
  });
}

function showConsole() {
  if ($('#gate')) $('#gate').hidden = true;
  $('#console').hidden = false;
  if (!REPLAY) connectStream();
  schedule();
}

// ---------------------------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------------------------

function boot() {
  let theme = 'dark';
  try { theme = localStorage.getItem('agentgov-theme') || 'dark'; } catch (e) { /* default dark */ }
  document.documentElement.dataset.theme = theme;
  if (REPLAY) {
    document.body.classList.add('replay');
    const m = REPLAY.meta || {};
    const banner = document.createElement('div');
    banner.className = 'replay-banner';
    banner.textContent = `Recorded from a live run on ${String(m.recorded_at || '').slice(0, 16).replace('T', ' ')} · models ${m.agent_model || '?'} / ${m.investigator_model || '?'} · playback only`;
    document.body.prepend(banner);
    const events = REPLAY.events || [];
    ui.kvData = { meta: m, events, views: events.filter((e) => e.kind === 'keyview').map((e) => ({ ...e.payload, seq: e.seq, ts: e.ts })) };
    ui.state = fold(events);
    $('#console').hidden = false;
    ui.kvData.replay = REPLAY.replay || null;
    if (ui.kvData.replay) openReplay(false); else if (ui.kvData.views.length) enterKeyView(0); else schedule();
    return;
  }
  wireGate();
  api('GET', '/api/connection/status').then((c) => {
    ui.conn = c;
    if (c.run && c.run.exists) showConsole(); else showGate();
  });
}

boot();
