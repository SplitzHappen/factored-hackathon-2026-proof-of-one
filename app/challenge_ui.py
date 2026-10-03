from __future__ import annotations


def render_challenge_ui(*, llm_connected: bool) -> str:
    """Return the judge-facing full challenge-data shell."""

    interpreter = (
        "OpenAI GPT-6 Luna · deterministic policy authority retained"
        if llm_connected
        else "Deterministic interpreter · deterministic policy authority retained"
    )
    mode_badge = "LIVE LLM · FULL DATA" if llm_connected else "FULL DATA · LOCAL"

    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Proof of One — Full Challenge Data</title>
<style>
:root{
  color-scheme:dark;
  --cream:#f6edcf;
  --muted:#aebaa9;
  --line:rgba(246,237,207,.22);
  --panel:#152018;
  --panel2:#203026;
  --ink:#101610;
  --green:#34d477;
  --green2:#174829;
  --yellow:#ffd15c;
  --blue:#3f8cff;
  --red:#ff665c;
  --purple:#bb8cff;
  --rail:#d9decf;
  --rail-ink:#1e2a22;
  --shadow:0 26px 70px rgba(0,0,0,.36);
  font-family:"IBM Plex Mono","Cascadia Mono",Consolas,ui-monospace,monospace;
}
*{box-sizing:border-box}
body{
  margin:0;
  min-height:100vh;
  color:var(--cream);
  background:
    radial-gradient(circle at 10% 0%,rgba(57,110,70,.42),transparent 30rem),
    radial-gradient(circle at 90% 5%,rgba(116,83,41,.30),transparent 25rem),
    linear-gradient(145deg,#071008 0%,#111a13 55%,#172017 100%);
}
button,input,select,textarea{font:inherit}
.page{width:min(1540px,calc(100vw - 32px));margin:0 auto;padding:24px 0 34px}
.shell{overflow:hidden;border:1px solid rgba(246,237,207,.28);border-radius:28px;background:rgba(17,25,18,.94);box-shadow:var(--shadow)}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;padding:24px 28px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,rgba(14,27,16,.98),rgba(18,28,20,.92))}
.brand{display:grid;gap:8px}
.eyebrow{color:var(--muted);font-size:12px;font-weight:900;letter-spacing:.16em;text-transform:uppercase}
h1{margin:0;font-size:clamp(24px,4vw,44px);line-height:.98;letter-spacing:.11em;text-transform:uppercase;text-shadow:0 0 20px rgba(246,237,207,.18)}
.sub{margin:0;max-width:940px;color:var(--muted);font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:15px;line-height:1.45}
.badge{justify-self:end;min-width:188px;border:1px solid rgba(52,212,119,.65);border-radius:999px;padding:14px 18px;background:rgba(52,212,119,.16);font-weight:900;letter-spacing:.06em;text-align:center;text-transform:uppercase;white-space:nowrap}
.boundary{padding:12px 28px;border-bottom:1px solid var(--line);background:rgba(246,237,207,.06);color:#e7ddbd;font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.45}

.grid{display:grid;grid-template-columns:minmax(320px,410px) minmax(0,1fr);gap:18px;padding:20px}
.stack{display:grid;gap:14px;align-content:start}
.panel{min-width:0;border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,rgba(32,48,38,.97),rgba(18,28,20,.98));box-shadow:0 14px 36px rgba(0,0,0,.23);padding:18px}
.panel h2{margin:0 0 14px;font-size:18px;letter-spacing:.12em;text-transform:uppercase}
.field{margin-bottom:12px}
.field label{display:block;margin-bottom:8px;color:var(--muted);font-size:12px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}
.row{display:flex;gap:10px}
.row>*{flex:1}
input,select,textarea{width:100%;border:1px solid rgba(246,237,207,.25);border-radius:14px;background:rgba(8,14,9,.72);color:var(--cream);padding:12px 13px}
select{min-height:44px}
textarea{min-height:118px;line-height:1.45;resize:vertical}
input::placeholder,textarea::placeholder{color:rgba(246,237,207,.46)}
button{width:100%;border:1px solid rgba(246,237,207,.28);border-radius:14px;background:#111810;color:var(--cream);cursor:pointer;font-weight:900;letter-spacing:.035em;padding:12px 14px;text-transform:uppercase}
button:hover:not(:disabled),button:focus-visible{outline:2px solid rgba(246,237,207,.36);outline-offset:2px;background:#1d281f}
button:disabled{opacity:.45;cursor:not-allowed}
.primary{background:#243623;border-color:rgba(52,212,119,.48)}
.secondary{background:rgba(32,48,38,.72)}
.handoff-btn{background:rgba(82,49,108,.72);border-color:rgba(187,140,255,.55)}
.revoke{background:rgba(92,38,34,.72);border-color:rgba(255,102,92,.55)}
.meta,.error,.micro{font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.45}
.meta{min-height:50px;border:1px solid rgba(246,237,207,.18);border-radius:16px;background:rgba(246,237,207,.07);color:var(--muted);padding:12px;overflow-wrap:anywhere}
.error{min-height:20px;color:#ffd8d5}
.micro{color:var(--muted)}
.coverage{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}
.metric{min-width:0;border:1px solid rgba(246,237,207,.18);border-radius:16px;background:rgba(246,237,207,.07);padding:10px}
.metric strong{display:block;color:var(--cream);font-size:16px}
.metric span{color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase}

.signal-board{
  overflow:hidden;
  border:1px solid rgba(246,237,207,.34);
  border-radius:28px;
  background:
    linear-gradient(180deg,rgba(222,227,211,.96),rgba(184,195,177,.95)),
    radial-gradient(circle at center,rgba(255,255,255,.35),transparent 32rem);
  color:var(--rail-ink);
  box-shadow:inset 0 0 0 1px rgba(0,0,0,.18),0 18px 50px rgba(0,0,0,.28);
}
.signal-top{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:start;padding:20px;border-bottom:4px solid rgba(30,42,34,.42)}
.signal-top .eyebrow{color:#405349}
.signal-title{margin-top:6px;color:#172119;font-size:clamp(25px,4vw,46px);font-weight:900;letter-spacing:.06em;line-height:.95;text-transform:uppercase}
.badge-row{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.route-badge{border:2px solid rgba(30,42,34,.46);border-radius:999px;background:rgba(255,255,255,.42);color:#26342b;padding:8px 11px;font-size:11px;font-weight:900;letter-spacing:.07em;text-transform:uppercase;white-space:nowrap}
.route-badge.intent{display:none}
.lines{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:14px 16px;border-bottom:4px solid rgba(30,42,34,.35)}
.line-card{min-height:170px;border:3px solid rgba(30,42,34,.50);border-radius:20px;background:rgba(238,241,229,.92);box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);padding:12px;display:grid;grid-template-rows:auto 1fr;gap:10px}
.line-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.line-name{font-size:11px;font-weight:900;letter-spacing:.09em;text-transform:uppercase;color:#536255}
.lamp-mini{width:28px;height:28px;flex:0 0 28px;border:4px solid #273026;border-radius:999px;background:#6d776b;box-shadow:inset 0 0 0 5px rgba(0,0,0,.10)}
.lamp-mini.on{background:#1c8e51;box-shadow:0 0 18px rgba(28,142,81,.35),inset 0 0 0 5px rgba(255,255,255,.08)}
.lamp-mini.warn{background:#c99822}
.lamp-mini.stop{background:#a93d35}
.line-card p{margin:0;font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.42;color:#29382f}
.board-main{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,360px);gap:14px;padding:16px}
.route-panel{border:4px solid #172119;border-radius:24px;background:#0f160f;color:var(--cream);padding:18px;box-shadow:inset 0 0 0 1px rgba(246,237,207,.12)}
.route-line{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;margin-bottom:14px}
.route{font-size:clamp(40px,7vw,76px);font-weight:900;letter-spacing:.06em;line-height:.92;text-transform:uppercase}
.lamp{width:58px;height:58px;border:6px solid #2b332a;border-radius:999px;background:#5e685c;box-shadow:inset 0 0 0 8px rgba(0,0,0,.12)}
.lamp.on{background:#24af63;box-shadow:0 0 0 7px rgba(36,175,99,.18),0 0 34px rgba(36,175,99,.42)}
.response{min-height:112px;white-space:pre-wrap;line-height:1.55;border:1px solid rgba(246,237,207,.2);border-radius:18px;background:rgba(246,237,207,.06);padding:16px;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
.response.answer{border-color:rgba(52,212,119,.45)}
.response.clarify{border-color:rgba(255,209,92,.55)}
.response.escalate{border-color:rgba(255,102,92,.55)}
.response.abstain{border-color:rgba(160,176,156,.55)}
.side-board{display:grid;gap:12px}
.why,.evidence-card{border:3px solid rgba(30,42,34,.42);border-radius:22px;background:rgba(238,241,229,.96);padding:14px;color:#26342b}
.why h3,.evidence-card h3{margin:0 0 8px;font-size:12px;letter-spacing:.12em;text-transform:uppercase}
.why p{margin:0;font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.45}
.evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.evidence div{min-height:62px;display:grid;align-content:start;gap:5px;overflow-wrap:anywhere;border:1px solid rgba(30,42,34,.22);border-radius:14px;background:rgba(255,255,255,.42);padding:9px;font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:12px;line-height:1.3}
.evidence b{color:#556458;font-family:"IBM Plex Mono","Cascadia Mono",Consolas,ui-monospace,monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.history{margin-top:14px}
.history-item{border-top:1px solid var(--line);padding:10px 0;color:var(--muted);font-size:13px}
.limits{border-top:1px solid var(--line);padding:14px 24px 18px;color:var(--muted);font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:12px;line-height:1.45;text-align:center}

@media(max-width:1180px){.lines{grid-template-columns:repeat(2,minmax(0,1fr))}.board-main{grid-template-columns:1fr}}
@media(max-width:980px){.grid{grid-template-columns:1fr}.topbar{grid-template-columns:1fr}.badge{justify-self:start}.badge-row{justify-content:flex-start}}
@media(max-width:640px){.page{width:min(100vw - 18px,1540px);padding-top:10px}.grid{padding:12px}.row{flex-direction:column}.coverage,.evidence,.lines{grid-template-columns:1fr}.signal-top{grid-template-columns:1fr}.route-line{grid-template-columns:1fr}.lamp{justify-self:start}}
</style>
</head>
<body>
<main class="page">
<section class="shell">
<header class="topbar">
  <div class="brand">
    <div class="eyebrow">Proof of One</div>
    <h1>Full challenge-data signal box</h1>
    <p class="sub">Search a challenge customer by ID, replay a provided customer message or type a new Spanish/Portuguese request, and inspect how the railway-style interlock clears, clarifies, escalates, or blocks the route.</p>
  </div>
  <div class="badge">__MODE_BADGE__</div>
</header>
<div class="boundary">Full challenge data · read-only · customer-scoped · language auto-detected · deterministic route authority · not fraud detection · not production/pilot-ready</div>

<section class="grid">
<aside class="stack">
  <div class="panel">
    <h2>Challenge data</h2>
    <div id="coverageStatus" class="micro">Loading coverage…</div>
    <div id="coverage" class="coverage"></div>
  </div>

  <div class="panel">
    <h2>Customer controls</h2>
    <div class="field">
      <label for="customerQuery">Customer ID</label>
      <div class="row">
        <input id="customerQuery" placeholder="Search customer ID prefix">
        <button id="searchCustomer" class="primary" type="button">Search</button>
      </div>
    </div>
    <div class="field">
      <label for="customerSelect">Matching customer</label>
      <select id="customerSelect"></select>
    </div>
    <button id="startSession" class="primary" type="button">Start scoped session</button>
    <div id="sessionBox" class="meta" style="margin-top:10px">No active challenge session.</div>
    <div id="error" class="error"></div>
  </div>

  <div class="panel">
    <h2>Provided messages</h2>
    <div class="field">
      <label for="providedMessage">Customer transcript</label>
      <select id="providedMessage" disabled></select>
    </div>
    <div class="row">
      <button id="useMessage" class="secondary" type="button" disabled>Use selected</button>
      <button id="loadMore" class="secondary" type="button" disabled>Load more</button>
    </div>
    <p class="micro">Messages are loaded only for the active customer. Agent text and direct customer identifiers are not exposed in this selector.</p>
  </div>
</aside>

<section class="stack">
  <div class="panel">
    <h2>Customer message</h2>
    <div class="field">
      <textarea id="message" placeholder="Replay a provided message or type a new Spanish/Portuguese request."></textarea>
    </div>
    <div class="row">
      <button id="send" class="primary" type="button" disabled>Set route · send</button>
      <button id="handoff" class="handoff-btn" type="button" disabled>Handoff lane</button>
      <button id="revoke" class="revoke" type="button" disabled>Revoke session</button>
    </div>
  </div>

  <section class="signal-board" aria-label="railway interlocking board">
    <div class="signal-top">
      <div>
        <div class="eyebrow">Interlocking tower · deterministic policy</div>
        <div class="signal-title">Railway signal board</div>
      </div>
      <div class="badge-row">
        <span id="activeLine" class="route-badge">No active line</span>
        <span id="intentBadge" class="route-badge intent"></span>
        <span class="route-badge">Full data</span>
      </div>
    </div>

    <div class="lines" aria-label="ordered route checks">
      <article id="cardInterpret" class="line-card">
        <div class="line-head"><span class="line-name">1 · Interpreter</span><span id="lampInterpret" class="lamp-mini"></span></div>
        <p id="lineInterpret">Awaiting customer message.</p>
      </article>
      <article id="cardScope" class="line-card">
        <div class="line-head"><span class="line-name">2 · Customer scope</span><span id="lampScope" class="lamp-mini"></span></div>
        <p id="lineScope">No customer-scoped reference checked yet.</p>
      </article>
      <article id="cardAuthority" class="line-card">
        <div class="line-head"><span class="line-name">3 · Route authority</span><span id="lampAuthority" class="lamp-mini"></span></div>
        <p id="lineAuthority">Deterministic checks have not fired.</p>
      </article>
      <article id="cardVerify" class="line-card">
        <div class="line-head"><span class="line-name">4 · Act → verify</span><span id="lampVerify" class="lamp-mini"></span></div>
        <p id="lineVerify">No bounded action evidence yet.</p>
      </article>
    </div>

    <div class="board-main">
      <section class="route-panel">
        <div class="route-line">
          <div id="route" class="route">WAITING</div>
          <div id="mainLamp" class="lamp"></div>
        </div>
        <div id="interpreter" class="micro" style="margin-bottom:10px">Interpreter: __INTERPRETER__</div>
        <div id="response" class="response">Start a scoped customer session, then send a provided or custom message.</div>
      </section>

      <aside class="side-board">
        <section class="why">
          <h3>Why this route</h3>
          <p id="whyText">No route has cleared yet. Start a scoped customer session and send a customer message.</p>
        </section>
        <section class="evidence-card">
          <h3>Decision evidence</h3>
          <div id="evidence" class="evidence"></div>
        </section>
      </aside>
    </div>
  </section>

  <div class="panel history">
    <h2>Session turns</h2>
    <div id="turns" class="micro">No turns yet.</div>
  </div>
</section>
</section>

<footer class="limits">Boundary: full challenge data · customer-scoped read-only records · deterministic route authority · not fraud detection · no production or pilot readiness claim · no final submission/go-live claim.</footer>
</section>
</main>

<script>
(() => {
  const state = {customers: [], customer: null, session: null, messages: [], messageOffset: 0, lastResponse: null, turns: []};

  const els = {
    coverageStatus: document.getElementById('coverageStatus'),
    coverage: document.getElementById('coverage'),
    customerQuery: document.getElementById('customerQuery'),
    searchCustomer: document.getElementById('searchCustomer'),
    customerSelect: document.getElementById('customerSelect'),
    startSession: document.getElementById('startSession'),
    sessionBox: document.getElementById('sessionBox'),
    error: document.getElementById('error'),
    providedMessage: document.getElementById('providedMessage'),
    useMessage: document.getElementById('useMessage'),
    loadMore: document.getElementById('loadMore'),
    message: document.getElementById('message'),
    send: document.getElementById('send'),
    handoff: document.getElementById('handoff'),
    revoke: document.getElementById('revoke'),
    activeLine: document.getElementById('activeLine'),
    intentBadge: document.getElementById('intentBadge'),
    lineInterpret: document.getElementById('lineInterpret'),
    lineScope: document.getElementById('lineScope'),
    lineAuthority: document.getElementById('lineAuthority'),
    lineVerify: document.getElementById('lineVerify'),
    lampInterpret: document.getElementById('lampInterpret'),
    lampScope: document.getElementById('lampScope'),
    lampAuthority: document.getElementById('lampAuthority'),
    lampVerify: document.getElementById('lampVerify'),
    route: document.getElementById('route'),
    mainLamp: document.getElementById('mainLamp'),
    response: document.getElementById('response'),
    whyText: document.getElementById('whyText'),
    evidence: document.getElementById('evidence'),
    turns: document.getElementById('turns')
  };

  function setError(message) { els.error.textContent = message || ''; }

  async function api(path, options = {}) {
    const headers = Object.assign({'Content-Type': 'application/json'}, options.headers || {});
    if (state.session) headers['X-Demo-Session'] = state.session.session_id;
    const response = await fetch(path, Object.assign({}, options, {headers}));
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } catch (_) {}
      throw new Error(detail || ('HTTP ' + response.status));
    }
    if (response.status === 204) return null;
    return response.json();
  }

  function clearChildren(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function option(value, text) {
    const node = document.createElement('option');
    node.value = value;
    node.textContent = text;
    return node;
  }

  function humanize(value) {
    if (value === undefined || value === null || value === '') return '—';
    return String(value).replace(/_/g, ' ');
  }

  function routeClass(route) {
    return String(route || '').toLowerCase();
  }

  function setLamp(node, stateName) {
    node.className = 'lamp-mini';
    if (stateName) node.classList.add(stateName);
  }

  function setMainLamp(on) {
    els.mainLamp.classList.toggle('on', Boolean(on));
  }

  function renderCoverage(data) {
    clearChildren(els.coverage);
    const counts = data?.table_counts || {};
    const preferred = [
      ['customers','Customers'],
      ['transactions','Transactions'],
      ['call_transcripts','Messages'],
      ['call_center_interactions','Interactions'],
      ['complaints','Complaints'],
      ['digital_events','Digital events']
    ];
    for (const [key,label] of preferred) {
      if (!(key in counts)) continue;
      const metric = document.createElement('div');
      metric.className = 'metric';
      const strong = document.createElement('strong');
      strong.textContent = Number(counts[key]).toLocaleString();
      const span = document.createElement('span');
      span.textContent = label;
      metric.append(strong, span);
      els.coverage.appendChild(metric);
    }
    els.coverageStatus.textContent = data?.full_challenge_data
      ? 'Full challenge artifact available server-side.'
      : 'Full challenge artifact unavailable.';
  }

  function renderCustomers() {
    clearChildren(els.customerSelect);
    if (!state.customers.length) {
      els.customerSelect.appendChild(option('', 'No matching customer IDs'));
      return;
    }
    for (const customer of state.customers) {
      const label = customer.customer_id + ' · ' +
        (customer.country || 'country n/a') + ' · ' +
        customer.transcript_count + ' messages';
      els.customerSelect.appendChild(option(customer.customer_id, label));
    }
  }

  function renderSession() {
    if (!state.session) {
      els.sessionBox.textContent = 'No active challenge session.';
      els.send.disabled = true;
      els.handoff.disabled = true;
      els.revoke.disabled = true;
      els.providedMessage.disabled = true;
      els.useMessage.disabled = true;
      els.loadMore.disabled = true;
      return;
    }
    els.sessionBox.textContent =
      state.session.display_name + ' · ' +
      state.session.language.toUpperCase() + ' profile fallback · ' +
      state.session.transcript_count + ' provided messages · read-only scoped session';
    els.send.disabled = false;
    els.handoff.disabled = false;
    els.revoke.disabled = false;
    els.providedMessage.disabled = state.messages.length === 0;
    els.useMessage.disabled = state.messages.length === 0;
    els.loadMore.disabled = state.messages.length === 0;
  }

  function renderMessages() {
    clearChildren(els.providedMessage);
    if (!state.messages.length) {
      els.providedMessage.appendChild(option('', 'No provided customer messages'));
      renderSession();
      return;
    }
    state.messages.forEach((message, index) => {
      const preview = message.customer_text.length > 92
        ? message.customer_text.slice(0, 89) + '…'
        : message.customer_text;
      els.providedMessage.appendChild(
        option(String(index), (message.process_date || 'date n/a') + ' · ' + preview)
      );
    });
    renderSession();
  }

  function evidenceItem(label, value) {
    const box = document.createElement('div');
    const title = document.createElement('b');
    title.textContent = label;
    const body = document.createTextNode(value == null ? '—' : String(value));
    box.append(title, body);
    return box;
  }

  function whyFor(response) {
    const route = response?.route;
    const e = response?.decision_evidence || {};
    if (route === 'ANSWER') return 'The interlock cleared ANSWER because the request stayed inside the supported workflow and customer-scoped records could support a bounded response.';
    if (route === 'CLARIFY') return 'The interlock held the signal at CLARIFY because the system could not establish one safe verified reference without asking the customer for more detail.';
    if (route === 'ESCALATE') return 'The interlock routed to ESCALATE because the customer reported an issue that belongs in human review. This is not fraud detection.';
    if (route === 'ABSTAIN') return 'The interlock blocked the route because the request is unsupported, unsafe, or outside the bounded banking workflow.';
    if (route === 'HANDOFF') return 'The handoff lane created support-ticket evidence with persisted and read-back verification flags.';
    if (e.controlling_reason) return 'The deterministic interlock selected this route because: ' + humanize(e.controlling_reason) + '.';
    return 'No route has cleared yet. Start a scoped customer session and send a customer message.';
  }

  function renderEvidence(response) {
    clearChildren(els.evidence);
    if (!response) {
      for (const label of ['Route','Intent','Language','Reference','Control','Verify']) {
        els.evidence.appendChild(evidenceItem(label, 'waiting'));
      }
      return;
    }
    const e = response.decision_evidence || {};
    const verification = Array.isArray(e.verification_codes)
      ? e.verification_codes.join(' · ')
      : '—';
    const values = [
      ['Route', response.route],
      ['Intent', humanize(response.intent)],
      ['Language', e.language ? e.language.toUpperCase() : '—'],
      ['Reference', humanize(e.reference_status)],
      ['Control', humanize(e.controlling_reason || 'all checks clear')],
      ['Verify', verification],
      ['Action', humanize(e.action)],
      ['Execution', humanize(e.execution_status)]
    ];
    for (const [label,value] of values) els.evidence.appendChild(evidenceItem(label,value));
  }

  function renderChecks(response) {
    if (!response) {
      els.activeLine.textContent = state.session ? state.session.language.toUpperCase() + ' profile' : 'No active line';
      els.intentBadge.style.display = 'none';
      els.lineInterpret.textContent = 'Awaiting customer message.';
      els.lineScope.textContent = state.session ? 'Scoped to ' + state.session.customer_id + '.' : 'No customer-scoped reference checked yet.';
      els.lineAuthority.textContent = 'Deterministic checks have not fired.';
      els.lineVerify.textContent = 'No bounded action evidence yet.';
      setLamp(els.lampInterpret, '');
      setLamp(els.lampScope, state.session ? 'on' : '');
      setLamp(els.lampAuthority, '');
      setLamp(els.lampVerify, '');
      return;
    }

    const e = response.decision_evidence || {};
    const route = response.route || 'WAITING';
    const language = e.language || state.session?.language || '';
    els.activeLine.textContent = language ? language.toUpperCase() + ' line' : 'Language line';
    els.intentBadge.textContent = humanize(response.intent || route);
    els.intentBadge.style.display = 'inline-block';

    els.lineInterpret.textContent =
      'Language ' + (language ? language.toUpperCase() : '—') +
      ' · intent ' + humanize(response.intent) +
      ' · status ' + humanize(e.interpretation_status);
    els.lineScope.textContent =
      'Customer-scoped records checked · reference ' + humanize(e.reference_status) + '.';
    els.lineAuthority.textContent =
      'Route authority: ' + route + ' · control ' + humanize(e.controlling_reason || 'all checks clear') + '.';

    const verification = Array.isArray(e.verification_codes) && e.verification_codes.length
      ? e.verification_codes.map(humanize).join(' · ')
      : 'no verification code returned';
    els.lineVerify.textContent =
      'Execution ' + humanize(e.execution_status) + ' · ' + verification + '.';

    setLamp(els.lampInterpret, 'on');
    setLamp(els.lampScope, route === 'CLARIFY' ? 'warn' : 'on');
    setLamp(els.lampAuthority, route === 'ABSTAIN' ? 'stop' : route === 'CLARIFY' ? 'warn' : 'on');
    setLamp(els.lampVerify, route === 'ABSTAIN' ? 'stop' : route === 'CLARIFY' ? 'warn' : 'on');
  }

  function renderResponse(response) {
    state.lastResponse = response;
    const route = response?.route || 'WAITING';
    els.route.textContent = route;
    setMainLamp(Boolean(response?.route));
    els.response.className = 'response';
    if (response?.route) els.response.classList.add(routeClass(response.route));
    els.response.textContent = response?.response_text ||
      'Start a scoped customer session, then send a provided or custom message.';
    els.whyText.textContent = whyFor(response);
    renderChecks(response);
    renderEvidence(response);
  }

  function renderTurns() {
    clearChildren(els.turns);
    if (!state.turns.length) {
      els.turns.textContent = 'No turns yet.';
      return;
    }
    for (const turn of state.turns) {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.textContent = turn.route + ' · ' + turn.message;
      els.turns.appendChild(item);
    }
  }

  async function loadCoverage() {
    renderCoverage(await api('/api/challenge/coverage', {headers: {}}));
  }

  async function searchCustomers() {
    setError('');
    const query = encodeURIComponent(els.customerQuery.value.trim());
    state.customers = await api('/api/challenge/customers?query=' + query + '&limit=20', {headers: {}});
    renderCustomers();
  }

  async function loadMessages(reset = true) {
    if (!state.session) return;
    if (reset) {
      state.messages = [];
      state.messageOffset = 0;
    }
    const rows = await api(
      '/api/challenge/customers/' + encodeURIComponent(state.session.customer_id) +
      '/messages?limit=25&offset=' + state.messageOffset,
      {headers: {}}
    );
    state.messages.push(...rows);
    state.messageOffset += rows.length;
    renderMessages();
    els.loadMore.disabled = rows.length < 25;
  }

  async function startSession() {
    setError('');
    const customerId = els.customerSelect.value;
    if (!customerId) throw new Error('Choose a challenge customer first.');
    state.session = await api('/api/challenge/sessions', {
      method: 'POST',
      headers: {},
      body: JSON.stringify({customer_id: customerId})
    });
    state.turns = [];
    state.lastResponse = null;
    renderResponse(null);
    renderTurns();
    await loadMessages(true);
    renderSession();
  }

  function useSelectedMessage() {
    const index = Number(els.providedMessage.value);
    const row = state.messages[index];
    if (row) els.message.value = row.customer_text;
  }

  async function sendTurn() {
    setError('');
    const message = els.message.value.trim();
    if (!message) return;
    const response = await api('/api/customer/turn', {
      method: 'POST',
      body: JSON.stringify({message})
    });
    state.turns.unshift({message, route: response.route});
    renderResponse(response);
    renderTurns();
  }

  async function handoff() {
    setError('');
    const response = await api('/api/customer/handoff', {
      method: 'POST',
      body: '{}'
    });
    const mapped = {
      route: 'HANDOFF',
      intent: 'customer requested support handoff',
      response_text: response.persisted && response.verified
        ? 'Support ticket persisted and read-back verified. Ticket: ' + response.ticket_id
        : 'Support ticket response received.',
      decision_evidence: {
        language: state.session?.language,
        interpretation_status: 'not invoked',
        reference_status: 'not applicable',
        controlling_reason: 'customer requested support',
        action: 'create support ticket',
        execution_status: response.persisted ? 'completed' : 'unknown',
        verification_codes: [
          response.persisted ? 'ticket persisted' : 'persistence unverified',
          response.verified ? 'read-back verified' : 'read-back unverified'
        ]
      }
    };
    state.turns.unshift({message: 'Customer requested support handoff', route: 'HANDOFF'});
    renderResponse(mapped);
    renderTurns();
  }

  async function revoke() {
    await api('/api/demo/session', {method: 'DELETE', body: '{}'});
    state.session = null;
    state.messages = [];
    state.messageOffset = 0;
    state.turns = [];
    renderMessages();
    renderSession();
    renderResponse(null);
    renderTurns();
  }

  els.searchCustomer.addEventListener('click', () => searchCustomers().catch(e => setError(e.message)));
  els.customerQuery.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchCustomers().catch(e => setError(e.message));
  });
  els.startSession.addEventListener('click', () => startSession().catch(e => setError(e.message)));
  els.useMessage.addEventListener('click', useSelectedMessage);
  els.loadMore.addEventListener('click', () => loadMessages(false).catch(e => setError(e.message)));
  els.send.addEventListener('click', () => sendTurn().catch(e => setError(e.message)));
  els.handoff.addEventListener('click', () => handoff().catch(e => setError(e.message)));
  els.revoke.addEventListener('click', () => revoke().catch(e => setError(e.message)));

  renderSession();
  renderResponse(null);
  renderTurns();
  Promise.all([loadCoverage(), searchCustomers()]).catch(e => setError(e.message));
})();
</script>
</body>
</html>"""

    return (
        html.replace("__INTERPRETER__", interpreter)
        .replace("__MODE_BADGE__", mode_badge)
    )
