from __future__ import annotations


DEMO_UI_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof of One — Signal Box Demo</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101710;
      --panel: #172319;
      --panel-2: #213027;
      --cream: #f5edcf;
      --cream-2: #e7ddbd;
      --ink: #101410;
      --muted: #aeb7a7;
      --line: rgba(245, 237, 207, 0.24);
      --rail: #485243;
      --answer: #37d67a;
      --clarify: #ffd15c;
      --abstain: #a9b1bd;
      --escalate: #ff665c;
      --handoff: #bb8cff;
      --shadow: 0 26px 70px rgba(0, 0, 0, 0.35);
      font-family: "IBM Plex Mono", "Cascadia Mono", "SFMono-Regular", Consolas, ui-monospace, monospace;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--cream);
      background:
        radial-gradient(circle at 15% 0%, rgba(80, 114, 82, 0.35), transparent 28rem),
        radial-gradient(circle at 90% 8%, rgba(122, 95, 49, 0.28), transparent 24rem),
        linear-gradient(145deg, #0b120d 0%, #111a13 54%, #161f17 100%);
      min-height: 100vh;
    }

    .page {
      width: min(1500px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 34px;
    }

    .shell {
      border: 1px solid rgba(245, 237, 207, 0.28);
      border-radius: 28px;
      overflow: hidden;
      background: rgba(17, 25, 18, 0.92);
      box-shadow: var(--shadow);
    }

    .topbar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: center;
      padding: 24px 28px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(15, 27, 16, 0.98), rgba(18, 28, 20, 0.92));
    }

    .brand {
      display: grid;
      gap: 8px;
    }

    .brand h1 {
      margin: 0;
      font-size: clamp(24px, 4vw, 44px);
      line-height: 0.96;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      color: var(--cream);
      text-shadow: 0 0 20px rgba(245, 237, 207, 0.18);
    }

    .brand p {
      margin: 0;
      max-width: 870px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.45;
    }

    .route-token {
      justify-self: end;
      min-width: 190px;
      text-align: center;
      padding: 14px 18px;
      border-radius: 999px;
      border: 1px solid rgba(245, 237, 207, 0.22);
      color: var(--cream);
      background: rgba(255, 255, 255, 0.08);
      font-size: 20px;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .route-token.answer { background: rgba(55, 214, 122, 0.16); border-color: rgba(55, 214, 122, 0.65); }
    .route-token.clarify { background: rgba(255, 209, 92, 0.15); border-color: rgba(255, 209, 92, 0.7); }
    .route-token.abstain { background: rgba(169, 177, 189, 0.13); border-color: rgba(169, 177, 189, 0.6); }
    .route-token.escalate { background: rgba(255, 102, 92, 0.14); border-color: rgba(255, 102, 92, 0.7); }
    .route-token.handoff { background: rgba(187, 140, 255, 0.16); border-color: rgba(187, 140, 255, 0.7); }

    .main {
      display: grid;
      grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
      gap: 18px;
      padding: 20px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(33, 48, 39, 0.96), rgba(19, 29, 21, 0.98));
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
    }

    .controls {
      padding: 20px;
      display: grid;
      gap: 14px;
      align-content: start;
    }

    .section-title {
      margin: 0;
      color: var(--cream);
      font-size: 19px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .field label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    select,
    textarea,
    button {
      width: 100%;
      font: inherit;
      border-radius: 14px;
    }

    select,
    textarea {
      color: var(--cream);
      border: 1px solid rgba(245, 237, 207, 0.25);
      background: rgba(8, 14, 9, 0.72);
      padding: 12px 13px;
    }

    textarea {
      min-height: 96px;
      resize: vertical;
      line-height: 1.45;
    }

    button {
      border: 1px solid rgba(245, 237, 207, 0.28);
      color: var(--cream);
      background: #111810;
      padding: 12px 14px;
      cursor: pointer;
      font-weight: 900;
      letter-spacing: 0.035em;
      text-transform: uppercase;
    }

    button:hover:not(:disabled), button:focus-visible {
      outline: 2px solid rgba(245, 237, 207, 0.36);
      outline-offset: 2px;
      background: #1d281f;
    }

    button:disabled { opacity: 0.45; cursor: not-allowed; }
    .primary { background: #243623; border-color: rgba(55, 214, 122, 0.48); }
    .handoff-btn { background: rgba(82, 49, 108, 0.72); border-color: rgba(187, 140, 255, 0.55); }
    .revoke { background: rgba(92, 38, 34, 0.72); border-color: rgba(255, 102, 92, 0.55); }

    .session-box,
    .error {
      border-radius: 16px;
      padding: 12px;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
      line-height: 1.45;
    }

    .session-box {
      color: var(--muted);
      background: rgba(245, 237, 207, 0.07);
      border: 1px solid rgba(245, 237, 207, 0.18);
      overflow-wrap: anywhere;
    }

    .error {
      color: #ffd8d5;
      border: 1px solid rgba(255, 102, 92, 0.45);
      background: rgba(255, 102, 92, 0.10);
    }

    .scenario-grid {
      display: grid;
      gap: 10px;
    }

    .scenario {
      text-align: left;
      text-transform: none;
      letter-spacing: 0;
      border-left-width: 6px;
    }

    .scenario small {
      display: block;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-weight: 500;
      margin-top: 4px;
      line-height: 1.35;
    }

    .scenario.answer { border-left-color: var(--answer); }
    .scenario.clarify { border-left-color: var(--clarify); }
    .scenario.abstain { border-left-color: var(--abstain); }
    .scenario.escalate { border-left-color: var(--escalate); }
    .scenario.pt { border-left-color: var(--handoff); }

    .workbench {
      display: grid;
      gap: 18px;
    }

    .signal-board {
      overflow: hidden;
      padding: 20px;
      background:
        linear-gradient(180deg, rgba(224, 229, 211, 0.94), rgba(191, 201, 183, 0.94)),
        radial-gradient(circle at center, rgba(255,255,255,0.3), transparent 30rem);
      color: #1e2d25;
    }

    .signal-head {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 18px;
    }

    .signal-head h2 {
      margin: 0 0 10px;
      color: #142016;
      font-size: clamp(24px, 3vw, 36px);
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .signal-head p {
      margin: 0;
      max-width: 850px;
      color: #35483f;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.45;
    }

    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 8px 11px;
      background: #101610;
      color: var(--cream);
      font-weight: 900;
      letter-spacing: 0.055em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .lines {
      display: grid;
      grid-template-columns: minmax(190px, 240px) minmax(0, 1fr);
      gap: 16px;
      align-items: stretch;
      margin: 22px 0;
    }

    .line-card {
      border: 3px solid #1a211b;
      border-radius: 26px;
      background: #101610;
      color: var(--cream);
      padding: 22px;
      display: grid;
      align-content: center;
      gap: 12px;
      min-height: 160px;
    }

    .line-card b {
      font-size: 27px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .line-card span {
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 18px;
      line-height: 1.3;
    }

    .checks {
      position: relative;
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 12px;
      align-items: stretch;
    }

    .checks::before {
      content: "";
      position: absolute;
      left: -22px;
      right: 8px;
      top: 50%;
      height: 10px;
      border-radius: 999px;
      background: rgba(72, 82, 67, 0.45);
      transform: translateY(-50%);
      z-index: 0;
    }

    .check {
      position: relative;
      z-index: 1;
      min-height: 150px;
      border: 3px solid rgba(30, 43, 35, 0.42);
      border-radius: 22px;
      background: rgba(236, 239, 225, 0.96);
      padding: 15px 14px;
      display: grid;
      gap: 10px;
      align-content: space-between;
      color: #26322a;
      overflow: hidden;
    }

    .check.on {
      border-color: #141a14;
      box-shadow: 0 0 0 3px rgba(255, 209, 92, 0.25), 0 14px 28px rgba(0, 0, 0, 0.2);
    }

    .check-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: start;
    }

    .check-num {
      font-size: 22px;
      font-weight: 900;
      color: #566357;
    }

    .lamp {
      width: 30px;
      height: 30px;
      border-radius: 999px;
      flex: 0 0 auto;
      border: 4px solid #242a24;
      background: #596555;
      box-shadow: inset 0 0 0 5px rgba(0, 0, 0, 0.12);
    }

    .check.on .lamp { background: var(--clarify); box-shadow: 0 0 20px rgba(255, 209, 92, 0.72); }

    .check-title {
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-weight: 780;
      font-size: 14px;
      line-height: 1.22;
      color: #415044;
    }

    .check-state {
      justify-self: start;
      border-radius: 999px;
      background: rgba(34, 45, 36, 0.12);
      padding: 6px 10px;
      color: #657160;
      font-size: 13px;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .check.on .check-state { color: #161b14; background: rgba(255, 209, 92, 0.65); }

    .platforms {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 12px;
      margin: 16px 0 0;
    }

    .platform {
      min-height: 145px;
      border: 3px solid #181e18;
      border-radius: 26px;
      background: #f0ecd9;
      color: #111711;
      display: grid;
      justify-items: center;
      align-content: center;
      gap: 10px;
      text-align: center;
      padding: 12px;
    }

    .platform.active {
      transform: translateY(-2px);
      box-shadow: 0 0 0 4px rgba(20, 26, 20, 0.12), 0 20px 40px rgba(0,0,0,0.2);
    }

    .signal-lamp {
      width: 58px;
      height: 58px;
      border-radius: 999px;
      border: 6px solid #202720;
      background: #5b6859;
    }

    .platform.active.answer .signal-lamp { background: var(--answer); box-shadow: 0 0 26px rgba(55, 214, 122, 0.78); }
    .platform.active.clarify .signal-lamp { background: var(--clarify); box-shadow: 0 0 26px rgba(255, 209, 92, 0.78); }
    .platform.active.abstain .signal-lamp { background: var(--abstain); box-shadow: 0 0 24px rgba(169, 177, 189, 0.65); }
    .platform.active.escalate .signal-lamp { background: var(--escalate); box-shadow: 0 0 26px rgba(255, 102, 92, 0.78); }
    .platform.active.handoff .signal-lamp { background: var(--handoff); box-shadow: 0 0 26px rgba(187, 140, 255, 0.78); }

    .platform b {
      font-size: 22px;
      letter-spacing: 0.05em;
    }

    .platform span {
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.28;
    }

    .lower-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(310px, 0.95fr);
      gap: 18px;
    }

    .console {
      padding: 18px;
    }

    .console h3,
    .ledger h3 {
      margin: 0 0 12px;
      color: var(--cream);
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .turns {
      display: grid;
      gap: 12px;
    }

    .turn,
    .why-card,
    .record {
      border: 1px solid rgba(245, 237, 207, 0.18);
      border-radius: 18px;
      background: rgba(8, 14, 9, 0.58);
      padding: 14px;
    }

    .turn-user {
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.45;
      margin-bottom: 8px;
    }

    .turn-response {
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 16px;
      font-weight: 700;
      line-height: 1.45;
    }

    .why-card {
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.45;
    }

    .ledger {
      padding: 18px;
    }

    .kv {
      display: grid;
      gap: 9px;
      margin-bottom: 14px;
    }

    .kv div {
      display: grid;
      grid-template-columns: 125px 1fr;
      gap: 10px;
      border-bottom: 1px solid rgba(245, 237, 207, 0.12);
      padding-bottom: 8px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 14px;
    }

    .kv b { color: var(--cream); overflow-wrap: anywhere; }

    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .pill {
      display: inline-flex;
      border-radius: 999px;
      padding: 5px 8px;
      color: var(--cream);
      background: rgba(245, 237, 207, 0.09);
      border: 1px solid rgba(245, 237, 207, 0.16);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      overflow-wrap: anywhere;
    }

    .records {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }

    .record dl {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 10px;
      margin: 8px 0 0;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
    }

    .record dt { color: var(--muted); }
    .record dd { margin: 0; text-align: right; color: var(--cream); overflow-wrap: anywhere; }

    .limits {
      margin-top: 18px;
      border-top: 1px solid var(--line);
      padding: 14px 20px 18px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
      line-height: 1.45;
    }

    .empty { color: var(--muted); font-family: Inter, ui-sans-serif, system-ui, sans-serif; }

    @media (max-width: 1180px) {
      .main { grid-template-columns: 1fr; }
      .controls { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .controls .full { grid-column: 1 / -1; }
    }

    @media (max-width: 980px) {
      .checks { grid-template-columns: repeat(2, minmax(150px, 1fr)); }
      .platforms { grid-template-columns: repeat(2, minmax(150px, 1fr)); }
      .lower-grid { grid-template-columns: 1fr; }
      .lines { grid-template-columns: 1fr; }
      .checks::before { display: none; }
      .topbar, .signal-head { grid-template-columns: 1fr; }
      .route-token { justify-self: start; }
    }

    @media (max-width: 640px) {
      .page { width: 100%; padding: 0; }
      .shell { border-radius: 0; }
      .main { padding: 12px; }
      .controls { grid-template-columns: 1fr; }
      .checks, .platforms { grid-template-columns: 1fr; }
      .kv div { grid-template-columns: 1fr; }
      .topbar { padding: 18px; }
      .signal-board { padding: 14px; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="shell">
      <header class="topbar">
        <div class="brand">
          <h1>Proof of One</h1>
          <p>Railway signal-box prototype for a bounded bilingual payment-support workflow. The lamps are computed from the local synthetic API response, not from static design placeholders.</p>
        </div>
        <div id="route-token" class="route-token">No route set</div>
      </header>

      <section class="main">
        <aside class="card controls" aria-label="demo controls">
          <h2 class="section-title full">Signal controls</h2>
          <div class="field">
            <label for="persona">Customer</label>
            <select id="persona"></select>
          </div>
          <div class="field">
            <label for="language">Language</label>
            <select id="language">
              <option value="">Persona default</option>
              <option value="es">Spanish</option>
              <option value="pt">Portuguese</option>
            </select>
          </div>
          <button id="start-session" class="primary full">Start synthetic session</button>
          <button id="handoff" class="handoff-btn" disabled>Handoff lane</button>
          <button id="revoke" class="revoke" disabled>Revoke</button>
          <div id="session-box" class="session-box full">No active synthetic session.</div>
          <div id="error-box" class="error full" hidden></div>

          <div class="field full">
            <label for="message">Customer message</label>
            <textarea id="message" placeholder="Choose a scenario, then send to the local API…"></textarea>
          </div>
          <button id="send" disabled class="primary full">Set route</button>

          <div class="scenario-grid full" aria-label="demo scenarios">
            <button class="scenario answer" data-persona="lucia" data-message="¿Cuál es el estado de la transacción DEMO-ES-1001?">ANSWER · Known transaction<small>Verified synthetic record lookup.</small></button>
            <button class="scenario clarify" data-persona="lucia" data-message="Quiero consultar una transacción por 54000 COP.">CLARIFY · Two matches<small>Amount matches more than one synthetic transaction.</small></button>
            <button class="scenario escalate" data-persona="lucia" data-message="No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.">ESCALATE · Unauthorized report<small>Customer-reported issue; not fraud detection.</small></button>
            <button class="scenario abstain" data-persona="lucia" data-message="Quiero hacer una transferencia de 10000 COP a otra cuenta.">ABSTAIN · Unsupported action<small>Unsupported banking action request.</small></button>
            <button class="scenario pt" data-persona="rafael" data-message="Qual é o estado da transação DEMO-PT-2001?">PT · Rafael path<small>Portuguese path over synthetic data.</small></button>
          </div>
        </aside>

        <section class="workbench">
          <section class="card signal-board" aria-label="interlocking panel">
            <div class="signal-head">
              <div>
                <h2>Interlocking panel</h2>
                <p>Spanish and Portuguese messages enter the same fixed route boundary. Check lamps light only after the API response returns route evidence.</p>
              </div>
              <div class="badge-row">
                <span id="language-line" class="badge">ES/PT line</span>
                <span id="intent-badge" class="badge">No intent</span>
                <span class="badge">Visual prototype</span>
              </div>
            </div>

            <div class="lines">
              <div class="line-card"><b id="active-line">No line</b><span>interpreter → fixed checks</span></div>
              <div id="checks" class="checks"></div>
            </div>

            <div id="platforms" class="platforms"></div>
          </section>

          <section class="lower-grid">
            <section class="card console">
              <h3>Turn register</h3>
              <div id="turns" class="turns"><div class="empty">No message has been sent yet.</div></div>
            </section>
            <section class="card ledger">
              <h3>Why this route</h3>
              <div id="why" class="why-card">Waiting for backend response.</div>
              <div id="evidence" class="kv"></div>
              <div id="reason-pills" class="pill-row"></div>
              <div id="records" class="records"></div>
            </section>
          </section>
        </section>
      </section>

      <footer class="limits">
        Boundary: synthetic demo data only · local API visual prototype · no production or pilot readiness claim · no live-provider readiness claim · no fraud determination · no final submission/go-live claim · IPA-M1 remains open.
      </footer>
    </section>
  </main>

  <script>
    const checks = [
      ['unauthorized_activity_reported', 'Customer-reported unauthorized activity?'],
      ['possible_unauthorized_activity', 'Possible unauthorized activity failsafe?'],
      ['interpreter_unavailable', 'Interpreter unavailable?'],
      ['unsafe_or_excluded_record', 'Conflict, excluded relationship, or unsafe record?'],
      ['decline_explanation_request', 'Decline explanation request?'],
      ['prohibited_banking_action', 'Prohibited banking action?'],
      ['unsupported_intent', 'Unsupported intent?'],
      ['ambiguous_transaction_match', 'Multiple verified matches?']
    ];

    const platforms = [
      ['ANSWER', 'Verified answer', 'answer'],
      ['CLARIFY', 'Needs exact reference', 'clarify'],
      ['ABSTAIN', 'Unsupported / unsafe', 'abstain'],
      ['ESCALATE', 'Human review', 'escalate'],
      ['HANDOFF', 'Support ticket', 'handoff']
    ];

    const state = {personas: [], session: null, turns: [], lastResponse: null};

    const els = {
      routeToken: document.getElementById('route-token'),
      persona: document.getElementById('persona'),
      language: document.getElementById('language'),
      start: document.getElementById('start-session'),
      handoff: document.getElementById('handoff'),
      revoke: document.getElementById('revoke'),
      sessionBox: document.getElementById('session-box'),
      error: document.getElementById('error-box'),
      message: document.getElementById('message'),
      send: document.getElementById('send'),
      checks: document.getElementById('checks'),
      platforms: document.getElementById('platforms'),
      turns: document.getElementById('turns'),
      why: document.getElementById('why'),
      evidence: document.getElementById('evidence'),
      reasonPills: document.getElementById('reason-pills'),
      records: document.getElementById('records'),
      activeLine: document.getElementById('active-line'),
      languageLine: document.getElementById('language-line'),
      intentBadge: document.getElementById('intent-badge')
    };

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function routeClass(route) {
      const r = String(route || '').toLowerCase();
      return ['answer', 'clarify', 'abstain', 'escalate', 'handoff'].includes(r) ? r : '';
    }

    function setError(message) {
      els.error.hidden = !message;
      els.error.textContent = message || '';
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(state.session ? {'X-Demo-Session': state.session.session_id} : {}),
          ...(options.headers || {})
        }
      });
      if (response.status === 204) return null;
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
        throw new Error(detail || `HTTP ${response.status}`);
      }
      return body;
    }

    function formatMoney(value, currency) {
      if (value === undefined || value === null) return '—';
      const numeric = Number(value);
      if (Number.isNaN(numeric)) return `${value} ${currency || ''}`.trim();
      try {
        const locale = currency === 'BRL' ? 'pt-BR' : currency === 'COP' ? 'es-CO' : undefined;
        return new Intl.NumberFormat(locale, {style: 'currency', currency: currency || 'USD', currencyDisplay: 'code'}).format(numeric).replace(/\u00a0/g, ' ');
      } catch (error) {
        return `${numeric.toLocaleString()} ${currency || ''}`.trim();
      }
    }

    function formatTimestamp(value) {
      if (!value) return '—';
      return String(value).replace('T', ' ').slice(0, 16);
    }

    function computeWhy(response) {
      const route = response?.route;
      const reasons = response?.reason_codes || [];
      if (route === 'ANSWER') return 'The backend found a supported request over verified synthetic records for this session.';
      if (route === 'CLARIFY') return 'The backend found more than one verified possibility and refused to guess.';
      if (route === 'ESCALATE') return 'The customer reported unauthorized activity; the demo routes to human review. This is not a fraud determination.';
      if (route === 'ABSTAIN') return 'The request is outside the supported or safe demo boundary, so the system abstains.';
      if (route === 'HANDOFF') return 'The separate handoff endpoint created support-ticket evidence with persisted/verified flags.';
      if (reasons.length) return `Backend returned reason code(s): ${reasons.join(', ')}.`;
      return 'Waiting for backend response.';
    }

    function renderChecks(response) {
      const reasons = response?.reason_codes || [];
      els.checks.innerHTML = checks.map(([code, label], index) => {
        const on = reasons.includes(code);
        return `<article class="check ${on ? 'on' : ''}">
          <div class="check-head"><span class="check-num">${index + 1}</span><span class="lamp" aria-hidden="true"></span></div>
          <div class="check-title">${escapeHtml(label)}</div>
          <div class="check-state">${on ? 'ON' : 'OFF'}</div>
        </article>`;
      }).join('');
    }

    function renderPlatforms(route) {
      els.platforms.innerHTML = platforms.map(([name, sub, klass]) => {
        const active = route === name;
        return `<article class="platform ${klass} ${active ? 'active' : ''}">
          <span class="signal-lamp" aria-hidden="true"></span>
          <b>${name}</b>
          <span>${sub}</span>
        </article>`;
      }).join('');
    }

    function renderRecord(record) {
      return `<article class="record">
        <strong>${escapeHtml(record.transaction_id || record.product_id || 'Record')}</strong>
        <dl>
          ${record.occurred_at ? `<dt>Date</dt><dd>${escapeHtml(formatTimestamp(record.occurred_at))}</dd>` : ''}
          ${record.transaction_type ? `<dt>Type</dt><dd>${escapeHtml(record.transaction_type)}</dd>` : ''}
          ${record.status ? `<dt>Status</dt><dd>${escapeHtml(record.status)}</dd>` : ''}
          ${record.amount !== undefined ? `<dt>Amount</dt><dd>${escapeHtml(formatMoney(record.amount, record.currency))}</dd>` : ''}
          ${record.merchant_name ? `<dt>Merchant</dt><dd>${escapeHtml(record.merchant_name)}</dd>` : ''}
          ${record.product_type ? `<dt>Product</dt><dd>${escapeHtml(record.product_type)}</dd>` : ''}
          ${record.current_balance !== undefined ? `<dt>Balance</dt><dd>${escapeHtml(formatMoney(record.current_balance, record.currency))}</dd>` : ''}
        </dl>
      </article>`;
    }

    function renderEvidence(response) {
      const route = response?.route || 'NO ROUTE';
      const klass = routeClass(route);
      els.routeToken.textContent = route === 'NO ROUTE' ? 'No route set' : route;
      els.routeToken.className = `route-token ${klass}`;
      els.activeLine.textContent = state.session?.language ? `${state.session.language.toUpperCase()} line` : 'No line';
      els.languageLine.textContent = state.session?.language ? `${state.session.language.toUpperCase()} line` : 'ES/PT line';
      els.intentBadge.textContent = response?.intent && response.intent !== 'unknown' ? response.intent : 'No intent';
      els.why.textContent = computeWhy(response);
      const kv = [];
      kv.push(['Route', route]);
      if (response?.intent && response.intent !== 'unknown') kv.push(['Intent', response.intent]);
      if (response?.synthetic_data !== undefined) kv.push(['Synthetic', String(response.synthetic_data)]);
      if (response?.escalation_ticket_id) kv.push(['Ticket', response.escalation_ticket_id]);
      if (response?.ticket_id) kv.push(['Ticket', response.ticket_id]);
      if (response?.persisted !== undefined) kv.push(['Persisted', String(response.persisted)]);
      if (response?.verified !== undefined) kv.push(['Verified', String(response.verified)]);
      els.evidence.innerHTML = kv.map(([k, v]) => `<div><span>${escapeHtml(k)}</span><b>${escapeHtml(v)}</b></div>`).join('');
      const reasons = response?.reason_codes || [];
      els.reasonPills.innerHTML = reasons.map((reason) => `<span class="pill">${escapeHtml(reason)}</span>`).join('');
      const records = [...(response?.products || []), ...(response?.transactions || [])];
      const candidates = response?.clarification_transaction_ids || [];
      els.records.innerHTML = `${candidates.length ? `<article class="record"><strong>Clarification candidates</strong><div>${candidates.map(escapeHtml).join(', ')}</div></article>` : ''}${records.map(renderRecord).join('')}`;
      renderChecks(response);
      renderPlatforms(route);
    }

    function renderTurns() {
      if (!state.turns.length) {
        els.turns.innerHTML = '<div class="empty">No message has been sent yet.</div>';
        return;
      }
      els.turns.innerHTML = state.turns.map((turn) => `<article class="turn">
        ${turn.message ? `<div class="turn-user"><strong>Customer:</strong> ${escapeHtml(turn.message)}</div>` : ''}
        <div class="turn-response">${escapeHtml(turn.response?.response_text || turn.text || '')}</div>
      </article>`).join('');
    }

    function renderSession() {
      if (!state.session) {
        els.sessionBox.textContent = 'No active synthetic session.';
        els.send.disabled = true;
        els.handoff.disabled = true;
        els.revoke.disabled = true;
        return;
      }
      els.sessionBox.innerHTML = `<strong>${escapeHtml(state.session.display_name)}</strong><br>
        Session: ${escapeHtml(state.session.session_id)}<br>
        Role: ${escapeHtml(state.session.role)}<br>
        Language: ${escapeHtml(state.session.language)}<br>
        Synthetic: ${escapeHtml(state.session.synthetic_data)}`;
      els.send.disabled = false;
      els.handoff.disabled = false;
      els.revoke.disabled = false;
    }

    async function loadPersonas() {
      state.personas = await api('/api/demo/personas', {headers: {}});
      els.persona.innerHTML = state.personas.map((persona) => `<option value="${escapeHtml(persona.persona_id)}">${escapeHtml(persona.display_name)} · ${escapeHtml(persona.default_language.toUpperCase())}</option>`).join('');
    }

    async function startSession() {
      setError('');
      const body = {persona_id: els.persona.value};
      if (els.language.value) body.language = els.language.value;
      state.session = await api('/api/demo/sessions', {method: 'POST', headers: {}, body: JSON.stringify(body)});
      state.turns = [];
      state.lastResponse = null;
      renderSession();
      renderTurns();
      renderEvidence(null);
    }

    async function sendTurn() {
      setError('');
      const message = els.message.value.trim();
      if (!message) return;
      if (state.session && els.persona.value !== state.session.persona_id) {
        setError('The selected customer differs from the active session. Start a new session first.');
        return;
      }
      const response = await api('/api/customer/turn', {method: 'POST', body: JSON.stringify({message})});
      state.lastResponse = response;
      state.turns.unshift({message, response});
      renderTurns();
      renderEvidence(response);
    }

    async function requestHandoff() {
      setError('');
      const response = await api('/api/customer/handoff', {method: 'POST', body: '{}'});
      const text = response.persisted && response.verified
        ? `Support ticket created and verified. Ticket: ${response.ticket_id}`
        : `Support ticket response received. Ticket: ${response.ticket_id || 'not returned'}`;
      const mapped = {route: 'HANDOFF', intent: 'customer_requested_support_handoff', response_text: text, ticket_id: response.ticket_id, persisted: response.persisted, verified: response.verified, synthetic_data: state.session?.synthetic_data === true};
      state.lastResponse = mapped;
      state.turns.unshift({kind: 'HANDOFF', text, response: mapped});
      renderTurns();
      renderEvidence(mapped);
    }

    async function revokeSession() {
      setError('');
      await api('/api/demo/session', {method: 'DELETE', body: '{}'});
      state.session = null;
      state.turns = [];
      state.lastResponse = null;
      renderSession();
      renderTurns();
      renderEvidence(null);
    }

    els.start.addEventListener('click', () => startSession().catch((error) => setError(error.message)));
    els.send.addEventListener('click', () => sendTurn().catch((error) => setError(error.message)));
    els.handoff.addEventListener('click', () => requestHandoff().catch((error) => setError(error.message)));
    els.revoke.addEventListener('click', () => revokeSession().catch((error) => setError(error.message)));
    document.querySelectorAll('.scenario').forEach((button) => {
      button.addEventListener('click', () => {
        els.message.value = button.dataset.message || '';
        if (button.dataset.persona) els.persona.value = button.dataset.persona;
      });
    });

    loadPersonas().catch((error) => setError(error.message));
    renderChecks(null);
    renderPlatforms(null);
    renderSession();
    renderEvidence(null);
  </script>
</body>
</html>
'''


def render_demo_ui() -> str:
    """Return the dependency-free judge-facing local demo shell."""

    return DEMO_UI_HTML
