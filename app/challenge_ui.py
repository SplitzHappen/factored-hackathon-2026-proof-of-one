from __future__ import annotations


def render_challenge_ui(*, llm_connected: bool) -> str:
    """Return the judge-facing full challenge-data shell."""

    interpreter = (
        "OpenAI GPT-6 Luna · deterministic policy authority retained"
        if llm_connected
        else "Deterministic interpreter · deterministic policy authority retained"
    )
    mode_badge = "LIVE LLM · FULL DATA" if llm_connected else "FULL DATA · LOCAL"
    html = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Proof of One — Deterministic Support Interlock</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0c130d;
      --panel: #152018;
      --panel-2: #203026;
      --cream: #f6edcf;
      --cream-2: #e7ddbd;
      --ink: #101610;
      --muted: #adb7a7;
      --line: rgba(246, 237, 207, 0.22);
      --answer: #34d477;
      --clarify: #ffd15c;
      --abstain: #3f8cff;
      --clear: #1b7f4a;
      --waiting: #6d776b;
      --na: #8b9188;
      --escalate: #ff665c;
      --handoff: #bb8cff;
      --shadow: 0 26px 70px rgba(0, 0, 0, 0.36);
      font-family: "IBM Plex Mono", "Cascadia Mono", "SFMono-Regular", Consolas, ui-monospace, monospace;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--cream);
      background:
        radial-gradient(circle at 12% 0%, rgba(66, 105, 71, 0.38), transparent 30rem),
        radial-gradient(circle at 88% 4%, rgba(116, 83, 41, 0.30), transparent 25rem),
        linear-gradient(145deg, #08100a 0%, #111a13 54%, #172017 100%);
    }

    .page {
      width: min(1500px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 34px;
    }

    .shell {
      overflow: hidden;
      border: 1px solid rgba(246, 237, 207, 0.28);
      border-radius: 28px;
      background: rgba(17, 25, 18, 0.93);
      box-shadow: var(--shadow);
    }

    .topbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: center;
      padding: 24px 28px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(14, 27, 16, 0.98), rgba(18, 28, 20, 0.92));
    }

    .brand { display: grid; gap: 8px; min-width: 0; }

    .brand h1 {
      margin: 0;
      color: var(--cream);
      font-size: clamp(26px, 3.9vw, 48px);
      line-height: 0.98;
      letter-spacing: 0.10em;
      text-transform: uppercase;
      text-shadow: 0 0 20px rgba(246, 237, 207, 0.18);
      white-space: nowrap;
    }

    .brand p {
      margin: 0;
      max-width: 960px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.45;
    }

    .badge-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .badge {
      border: 1px solid rgba(246, 237, 207, 0.25);
      border-radius: 999px;
      padding: 14px 18px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--cream);
      font-size: 17px;
      font-weight: 900;
      letter-spacing: 0.06em;
      line-height: 1.1;
      text-align: center;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .main {
      display: grid;
      grid-template-columns: minmax(300px, 370px) minmax(0, 1fr);
      gap: 18px;
      padding: 20px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(32, 48, 38, 0.97), rgba(18, 28, 20, 0.98));
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.23);
    }

    .controls {
      display: grid;
      gap: 14px;
      align-content: start;
      padding: 20px;
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
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    input, select, textarea, button {
      width: 100%;
      border-radius: 14px;
      font: inherit;
    }

    input, select, textarea {
      border: 1px solid rgba(246, 237, 207, 0.25);
      background: rgba(8, 14, 9, 0.72);
      color: var(--cream);
      padding: 12px 13px;
    }

    textarea {
      min-height: 122px;
      line-height: 1.45;
      resize: vertical;
    }

    button {
      border: 1px solid rgba(246, 237, 207, 0.28);
      background: #111810;
      color: var(--cream);
      cursor: pointer;
      font-weight: 900;
      letter-spacing: 0.035em;
      padding: 12px 14px;
      text-transform: uppercase;
    }

    button:hover:not(:disabled), button:focus-visible {
      outline: 2px solid rgba(246, 237, 207, 0.36);
      outline-offset: 2px;
      background: #1d281f;
    }

    button:disabled { opacity: 0.45; cursor: not-allowed; }
    .primary { background: #243623; border-color: rgba(52, 212, 119, 0.48); }
    .human { background: rgba(82, 49, 108, 0.72); border-color: rgba(187, 140, 255, 0.55); }
    .revoke { background: rgba(92, 38, 34, 0.72); border-color: rgba(255, 102, 92, 0.55); }

    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

    .session-box, .error {
      border-radius: 16px;
      padding: 12px;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
      line-height: 1.45;
    }

    .session-box {
      color: var(--muted);
      background: rgba(246, 237, 207, 0.07);
      border: 1px solid rgba(246, 237, 207, 0.18);
      overflow-wrap: anywhere;
    }

    .error {
      display: none;
      color: #ffd8d5;
      border: 1px solid rgba(255, 102, 92, 0.45);
      background: rgba(255, 102, 92, 0.10);
    }

    .board {
      display: grid;
      grid-template-rows: auto auto auto;
      gap: 18px;
      min-width: 0;
    }

    .route-board {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 118px;
      grid-template-areas:
        "route lamp"
        "meta meta"
        "response response";
      gap: 18px;
      min-height: 330px;
      padding: 28px;
      border: 1px solid rgba(246, 237, 207, 0.22);
      border-radius: 28px;
      background: #08100a;
      box-shadow: inset 0 0 0 1px rgba(52, 212, 119, 0.06);
    }

    .route-word {
      grid-area: route;
      min-width: 0;
      align-self: start;
      color: var(--cream);
      font-size: clamp(50px, 7.9vw, 112px);
      font-weight: 1000;
      letter-spacing: 0.09em;
      line-height: 0.88;
      text-transform: uppercase;
      overflow: hidden;
      text-overflow: clip;
    }

    .lamp-wrap {
      grid-area: lamp;
      display: grid;
      place-items: start center;
      padding-top: 6px;
    }

    .lamp {
      width: 94px;
      height: 94px;
      border-radius: 50%;
      background: radial-gradient(circle at 50% 42%, #687466, #344033 56%, #182018 57%);
      border: 14px solid #3a4539;
      box-shadow: 0 0 0 10px rgba(52, 212, 119, 0.08), inset 0 0 18px rgba(0, 0, 0, 0.35);
    }

    .lamp.on.answer {
      background: radial-gradient(circle at 50% 42%, #37dc80, #25b766 58%, #145e39 59%);
      border-color: #28533a;
      box-shadow: 0 0 34px rgba(52, 212, 119, 0.74), 0 0 0 12px rgba(52, 212, 119, 0.16);
    }
    .lamp.on.clarify {
      background: radial-gradient(circle at 50% 42%, #ffe08a, #d59b25 58%, #6e4f12 59%);
      border-color: #66532a;
      box-shadow: 0 0 34px rgba(255, 209, 92, 0.70), 0 0 0 12px rgba(255, 209, 92, 0.16);
    }
    .lamp.on.escalate {
      background: radial-gradient(circle at 50% 42%, #ff746b, #bf3d37 58%, #5e1f1b 59%);
      border-color: #55302e;
      box-shadow: 0 0 34px rgba(255, 102, 92, 0.70), 0 0 0 12px rgba(255, 102, 92, 0.16);
    }
    .lamp.on.abstain {
      background: radial-gradient(circle at 50% 42%, #82b0ff, #3f8cff 58%, #244d8f 59%);
      border-color: #314762;
      box-shadow: 0 0 34px rgba(63, 140, 255, 0.70), 0 0 0 12px rgba(63, 140, 255, 0.16);
    }
    .lamp.on.handoff {
      background: radial-gradient(circle at 50% 42%, #cba4ff, #8d65dd 58%, #493071 59%);
      border-color: #4c3b61;
      box-shadow: 0 0 34px rgba(187, 140, 255, 0.70), 0 0 0 12px rgba(187, 140, 255, 0.16);
    }
    .lamp.on.waiting {
      background: radial-gradient(circle at 50% 42%, #9aa495, #65705f 58%, #2d362b 59%);
      border-color: #3a4539;
      box-shadow: 0 0 25px rgba(173, 183, 167, 0.38), 0 0 0 12px rgba(173, 183, 167, 0.10);
    }

    .status-copy {
      grid-area: meta;
      margin: 0;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 18px;
      line-height: 1.45;
    }

    .response {
      grid-area: response;
      border: 1px solid rgba(246, 237, 207, 0.24);
      border-radius: 22px;
      background: rgba(246, 237, 207, 0.05);
      padding: 24px;
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 24px;
      line-height: 1.52;
      min-height: 126px;
    }

    .route-board.busy .lamp { animation: pulse 1s infinite; }
    .route-board.busy .route-word { animation: scan 1.1s infinite; }

    @keyframes pulse { 0%, 100% { filter: brightness(0.85); } 50% { filter: brightness(1.55); } }
    @keyframes scan { 0%, 100% { opacity: 0.72; } 50% { opacity: 1; } }

    .lanes {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }

    .lane {
      border: 1px solid rgba(246, 237, 207, 0.20);
      border-radius: 18px;
      background: rgba(246, 237, 207, 0.055);
      color: var(--muted);
      padding: 14px;
      text-align: center;
      font-size: 17px;
      font-weight: 1000;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease, box-shadow 120ms ease;
    }

    .lane.active { color: var(--cream); transform: translateY(-2px); }
    .lane.answer.active { background: rgba(52, 212, 119, 0.16); border-color: rgba(52, 212, 119, 0.70); box-shadow: 0 0 26px rgba(52, 212, 119, 0.20); }
    .lane.clarify.active { background: rgba(255, 209, 92, 0.15); border-color: rgba(255, 209, 92, 0.72); box-shadow: 0 0 26px rgba(255, 209, 92, 0.18); }
    .lane.escalate.active { background: rgba(255, 102, 92, 0.14); border-color: rgba(255, 102, 92, 0.72); box-shadow: 0 0 26px rgba(255, 102, 92, 0.18); }
    .lane.abstain.active { background: rgba(63, 140, 255, 0.14); border-color: rgba(63, 140, 255, 0.70); box-shadow: 0 0 26px rgba(63, 140, 255, 0.18); }

    .checks {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
    }

    .check {
      min-height: 230px;
      border: 1px solid rgba(246, 237, 207, 0.20);
      border-radius: 24px;
      background: rgba(246, 237, 207, 0.06);
      padding: 22px 24px 20px;
      color: var(--cream-2);
      overflow: hidden;
    }

    .check-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 72px;
      gap: 16px;
      align-items: center;
      min-height: 72px;
    }

    .check-title {
      min-width: 0;
      max-width: 100%;
      color: var(--cream);
      font-size: clamp(21px, 1.55vw, 27px);
      line-height: 1.13;
      font-weight: 1000;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      overflow-wrap: normal;
      word-break: normal;
    }

    .mini-lamp {
      justify-self: end;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: radial-gradient(circle at 50% 42%, #5b6559, #303a30 58%, #151c16 59%);
      border: 10px solid #303a30;
      box-shadow: inset 0 0 16px rgba(0, 0, 0, 0.35);
    }

    .check.active .mini-lamp {
      background: radial-gradient(circle at 50% 42%, #37dc80, #25b766 58%, #145e39 59%);
      box-shadow: 0 0 25px rgba(52, 212, 119, 0.64);
    }
    .check.route-clarify.active .mini-lamp {
      background: radial-gradient(circle at 50% 42%, #ffe08a, #d59b25 58%, #6e4f12 59%);
      box-shadow: 0 0 25px rgba(255, 209, 92, 0.64);
    }
    .check.route-escalate.active .mini-lamp {
      background: radial-gradient(circle at 50% 42%, #ff746b, #bf3d37 58%, #5e1f1b 59%);
      box-shadow: 0 0 25px rgba(255, 102, 92, 0.64);
    }
    .check.route-abstain.active .mini-lamp {
      background: radial-gradient(circle at 50% 42%, #82b0ff, #3f8cff 58%, #244d8f 59%);
      box-shadow: 0 0 25px rgba(63, 140, 255, 0.64);
    }
    .check.busy .mini-lamp {
      background: radial-gradient(circle at 50% 42%, #ffe08a, #d59b25 58%, #6e4f12 59%);
      animation: pulse 1s infinite;
    }

    .check p {
      margin: 30px 0 0;
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 20px;
      line-height: 1.45;
    }

    .lower {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(330px, 440px);
      gap: 16px;
    }

    .why, .evidence { padding: 22px; }

    .why h2, .evidence h2 {
      margin: 0 0 18px;
      color: var(--cream);
      font-size: 22px;
      letter-spacing: 0.13em;
      text-transform: uppercase;
    }

    .why p {
      margin: 0;
      color: var(--cream-2);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 20px;
      line-height: 1.5;
    }

    .evidence { text-align: center; }

    .evidence-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .e-card {
      border: 1px solid rgba(246, 237, 207, 0.22);
      border-radius: 18px;
      background: rgba(246, 237, 207, 0.07);
      padding: 16px;
      min-height: 96px;
    }

    .e-card strong {
      display: block;
      text-align: center;
      color: var(--muted);
      font-size: 16px;
      font-weight: 1000;
      letter-spacing: 0.13em;
      text-transform: uppercase;
    }

    .e-card span {
      display: block;
      margin-top: 12px;
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 20px;
      overflow-wrap: anywhere;
    }

    .foot {
      padding: 0 20px 20px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
    }

    .hidden { display: none !important; }

    @media (max-width: 1120px) {
      .topbar, .main, .lower { grid-template-columns: 1fr; }
      .brand h1 { white-space: normal; }
      .checks { grid-template-columns: 1fr 1fr; }
    }

    @media (max-width: 720px) {
      .checks, .lanes, .evidence-grid { grid-template-columns: 1fr; }
      .route-board { grid-template-columns: 1fr; grid-template-areas: "lamp" "route" "meta" "response"; }
      .lamp-wrap { place-items: center; }
      .route-word { font-size: 46px; text-align: center; }
      .response { font-size: 20px; }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="shell">
      <header class="topbar">
        <div class="brand">
          <h1>Deterministic Support Interlock</h1>
          <p>Customer-scoped records · LLM interpretation · deterministic route authority · visible verification.</p>
        </div>
        <div class="badge-row">
          <div class="badge" id="languageBadge">ES/PT auto</div>
          <div class="badge" id="modeBadge">__MODE_BADGE__</div>
        </div>
      </header>

      <main class="main">
        <aside class="card controls">
          <h2 class="section-title">Challenge data</h2>

          <div class="field">
            <label for="customerQuery">Customer ID prefix</label>
            <input id="customerQuery" placeholder="Leave blank to list customers">
          </div>
          <button class="primary" id="searchCustomers">Search customers</button>

          <div class="field">
            <label for="customerSelect">Matching customer</label>
            <select id="customerSelect"></select>
          </div>

          <button class="primary" id="startSession">Start scoped session</button>
          <div class="session-box" id="sessionInfo">No customer session yet.</div>

          <div class="field">
            <label for="messageSelect">Provided messages</label>
            <select id="messageSelect"></select>
          </div>
          <button id="useMessage">Use selected message</button>

          <div class="field">
            <label for="message">Message</label>
            <textarea id="message" placeholder="Select a provided message or write a customer request."></textarea>
          </div>

          <button class="primary" id="sendMessage" disabled>Set route · send</button>
          <div class="two">
            <button class="human" id="humanReview" disabled>Human review</button>
            <button class="revoke" id="revokeSession" disabled>Revoke session</button>
          </div>

          <div class="error" id="errorBox"></div>
        </aside>

        <section class="board">
          <section class="route-board card" id="routeBoard">
            <div class="route-word" id="routeWord">WAITING</div>
            <div class="lamp-wrap"><div class="lamp" id="routeLamp" aria-hidden="true"></div></div>
            <p class="status-copy" id="statusCopy">Interpreter: __INTERPRETER__</p>
            <div class="response" id="responseText">Start a scoped customer session, then send a provided or custom message.</div>
          </section>

          <section class="lanes" aria-label="Route lanes">
            <div class="lane answer" id="laneANSWER">ANSWER</div>
            <div class="lane clarify" id="laneCLARIFY">CLARIFY</div>
            <div class="lane escalate" id="laneESCALATE">ESCALATE</div>
            <div class="lane abstain" id="laneABSTAIN">ABSTAIN</div>
          </section>

          <section class="checks">
            <article class="check" id="checkInterpreter">
              <div class="check-head">
                <div class="check-title">1 · Interpreter</div>
                <div class="mini-lamp" aria-hidden="true"></div>
              </div>
              <p id="copyInterpreter">Awaiting message.</p>
            </article>
            <article class="check" id="checkScope">
              <div class="check-head">
                <div class="check-title">2 · Customer scope</div>
                <div class="mini-lamp" aria-hidden="true"></div>
              </div>
              <p id="copyScope">No customer session yet.</p>
            </article>
            <article class="check" id="checkRoute">
              <div class="check-head">
                <div class="check-title">3 · Route authority</div>
                <div class="mini-lamp" aria-hidden="true"></div>
              </div>
              <p id="copyRoute">No route selected.</p>
            </article>
            <article class="check" id="checkAct">
              <div class="check-head">
                <div class="check-title">4 · Act → verify</div>
                <div class="mini-lamp" aria-hidden="true"></div>
              </div>
              <p id="copyAct">No action invoked.</p>
            </article>
          </section>

          <section class="lower">
            <article class="card why">
              <h2>Why this route</h2>
              <p id="whyText">The system is waiting for a scoped customer session and a customer message.</p>
            </article>

            <article class="card evidence">
              <h2>Decision evidence</h2>
              <div class="evidence-grid">
                <div class="e-card"><strong>Route</strong><span id="evRoute">WAITING</span></div>
                <div class="e-card"><strong>Intent</strong><span id="evIntent">none</span></div>
                <div class="e-card"><strong>Language</strong><span id="evLanguage">none</span></div>
                <div class="e-card"><strong>Reference</strong><span id="evReference">not checked</span></div>
                <div class="e-card"><strong>Control</strong><span id="evControl">none</span></div>
                <div class="e-card"><strong>Verify</strong><span id="evVerify">pending</span></div>
                <div class="e-card"><strong>Action</strong><span id="evAction">none</span></div>
                <div class="e-card"><strong>Execution</strong><span id="evExecution">not invoked</span></div>
              </div>
            </article>
          </section>
        </section>
      </main>

      <footer class="foot">
        Boundary: full challenge data · customer-scoped read-only records · deterministic policy authority retained · not fraud detection · not production/pilot-ready.
      </footer>
    </div>
  </div>

  <script>
    const els = {
      customerQuery: document.getElementById('customerQuery'),
      searchCustomers: document.getElementById('searchCustomers'),
      customerSelect: document.getElementById('customerSelect'),
      startSession: document.getElementById('startSession'),
      sessionInfo: document.getElementById('sessionInfo'),
      messageSelect: document.getElementById('messageSelect'),
      useMessage: document.getElementById('useMessage'),
      message: document.getElementById('message'),
      sendMessage: document.getElementById('sendMessage'),
      humanReview: document.getElementById('humanReview'),
      revokeSession: document.getElementById('revokeSession'),
      errorBox: document.getElementById('errorBox'),
      routeBoard: document.getElementById('routeBoard'),
      routeWord: document.getElementById('routeWord'),
      routeLamp: document.getElementById('routeLamp'),
      statusCopy: document.getElementById('statusCopy'),
      responseText: document.getElementById('responseText'),
      languageBadge: document.getElementById('languageBadge'),
      checkInterpreter: document.getElementById('checkInterpreter'),
      checkScope: document.getElementById('checkScope'),
      checkRoute: document.getElementById('checkRoute'),
      checkAct: document.getElementById('checkAct'),
      copyInterpreter: document.getElementById('copyInterpreter'),
      copyScope: document.getElementById('copyScope'),
      copyRoute: document.getElementById('copyRoute'),
      copyAct: document.getElementById('copyAct'),
      whyText: document.getElementById('whyText'),
      evRoute: document.getElementById('evRoute'),
      evIntent: document.getElementById('evIntent'),
      evLanguage: document.getElementById('evLanguage'),
      evReference: document.getElementById('evReference'),
      evControl: document.getElementById('evControl'),
      evVerify: document.getElementById('evVerify'),
      evAction: document.getElementById('evAction'),
      evExecution: document.getElementById('evExecution'),
      lanes: {
        ANSWER: document.getElementById('laneANSWER'),
        CLARIFY: document.getElementById('laneCLARIFY'),
        ESCALATE: document.getElementById('laneESCALATE'),
        ABSTAIN: document.getElementById('laneABSTAIN')
      }
    };

    const state = {
      customers: [],
      messages: [],
      session: null,
      busy: false
    };

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function sanitizeError(value) {
      return String(value ?? 'Request failed.')
        .replaceAll(/demo/gi, 'session')
        .replaceAll('Demo', 'Session');
    }

    function routeClass(route) {
      const normalized = String(route || 'WAITING').toUpperCase();
      if (normalized === 'ANSWER') return 'answer';
      if (normalized === 'CLARIFY') return 'clarify';
      if (normalized === 'ESCALATE') return 'escalate';
      if (normalized === 'ABSTAIN') return 'abstain';
      if (normalized === 'HANDOFF') return 'handoff';
      return 'waiting';
    }

    function showError(message) {
      els.errorBox.style.display = message ? 'block' : 'none';
      els.errorBox.textContent = message ? sanitizeError(message) : '';
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });
      if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
          const payload = await response.json();
          detail = payload.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }
      if (response.status === 204) return null;
      return await response.json();
    }

    function setControlsDisabled(disabled) {
      state.busy = disabled;
      els.searchCustomers.disabled = disabled;
      els.startSession.disabled = disabled || !els.customerSelect.value;
      els.useMessage.disabled = disabled || !els.messageSelect.value;
      els.sendMessage.disabled = disabled || !state.session;
      els.humanReview.disabled = disabled || !state.session;
      els.revokeSession.disabled = disabled || !state.session;
    }

    function resetLanes() {
      for (const lane of Object.values(els.lanes)) lane.classList.remove('active');
    }

    function setLamp(route, on = true) {
      els.routeLamp.className = `lamp ${on ? 'on ' + routeClass(route) : ''}`.trim();
    }

    function setChecksBusy() {
      for (const node of [els.checkInterpreter, els.checkScope, els.checkRoute, els.checkAct]) {
        node.className = 'check busy';
      }
      els.copyInterpreter.textContent = 'Interpreting customer language and intent.';
      els.copyScope.textContent = 'Confirming customer-scoped record boundary.';
      els.copyRoute.textContent = 'Setting deterministic route authority.';
      els.copyAct.textContent = 'Waiting for verified outcome.';
    }

    function clearCheckState() {
      els.checkInterpreter.className = 'check';
      els.checkScope.className = 'check';
      els.checkRoute.className = 'check';
      els.checkAct.className = 'check';
    }

    function setProcessing() {
      showError('');
      resetLanes();
      els.routeBoard.classList.add('busy');
      els.routeWord.textContent = 'SETTING';
      setLamp('CLARIFY', true);
      els.statusCopy.textContent = 'Interpreter: processing customer message · deterministic policy pending';
      els.responseText.textContent = 'Setting route authority. Please wait.';
      els.whyText.textContent = 'The interlock is interpreting the message, checking customer scope, and waiting for deterministic route authority.';
      setChecksBusy();
      setControlsDisabled(true);
    }

    function setInitialBoard() {
      els.routeBoard.classList.remove('busy');
      els.routeWord.textContent = 'WAITING';
      setLamp('WAITING', false);
      resetLanes();
      clearCheckState();
      els.statusCopy.textContent = 'Interpreter: __INTERPRETER__';
      els.responseText.textContent = 'Start a scoped customer session, then send a provided or custom message.';
      els.copyInterpreter.textContent = 'Awaiting message.';
      els.copyScope.textContent = state.session ? `Scoped to ${state.session.customer_id}.` : 'No customer session yet.';
      els.copyRoute.textContent = 'No route selected.';
      els.copyAct.textContent = 'No action invoked.';
      els.whyText.textContent = state.session
        ? 'A scoped customer session is active. Send a message to set the route.'
        : 'The system is waiting for a scoped customer session and a customer message.';
      els.evRoute.textContent = 'WAITING';
      els.evIntent.textContent = 'none';
      els.evLanguage.textContent = state.session?.language?.toUpperCase() || 'none';
      els.evReference.textContent = 'not checked';
      els.evControl.textContent = 'none';
      els.evVerify.textContent = 'pending';
      els.evAction.textContent = 'none';
      els.evExecution.textContent = 'not invoked';
    }

    function setRouteBoard(payload) {
      const route = String(payload.route || 'WAITING').toUpperCase();
      const evidence = payload.decision_evidence || {};
      const cls = routeClass(route);
      els.routeBoard.classList.remove('busy');
      els.routeWord.textContent = route;
      setLamp(route, true);
      resetLanes();
      if (els.lanes[route]) els.lanes[route].classList.add('active');

      const language = (evidence.language || state.session?.language || '').toString().toUpperCase();
      els.languageBadge.textContent = language ? `${language} detected` : 'ES/PT auto';
      els.statusCopy.textContent = `Interpreter: __INTERPRETER__`;
      els.responseText.textContent = payload.response_text || 'No response text returned.';

      clearCheckState();
      els.checkInterpreter.classList.add('active');
      els.checkScope.classList.add('active');
      els.checkRoute.classList.add('active', `route-${cls}`);
      els.checkAct.classList.add('active');

      els.copyInterpreter.textContent = `Language ${language || 'n/a'} · intent ${payload.intent || 'unknown'} · status ${evidence.interpretation_status || 'verified'}.`;
      els.copyScope.textContent = `Customer-scoped records checked · reference ${evidence.reference_status || 'not_required'}.`;
      els.copyRoute.textContent = `Route authority: ${route} · control ${evidence.controlling_reason || firstReason(payload) || 'deterministic policy'}.`;
      els.copyAct.textContent = `Action ${evidence.action || 'none'} · execution ${evidence.execution_status || 'not_invoked'}.`;

      els.whyText.textContent = whyFor(payload, evidence);
      els.evRoute.textContent = route;
      els.evIntent.textContent = payload.intent || 'unknown';
      els.evLanguage.textContent = language || 'n/a';
      els.evReference.textContent = evidence.reference_status || 'not_required';
      els.evControl.textContent = evidence.controlling_reason || firstReason(payload) || 'none';
      els.evVerify.textContent = (evidence.verification_codes || []).join(', ') || 'none';
      els.evAction.textContent = evidence.action || 'none';
      els.evExecution.textContent = evidence.execution_status || 'not_invoked';
    }

    function firstReason(payload) {
      return (payload.reason_codes || [])[0] || '';
    }

    function whyFor(payload, evidence) {
      const route = String(payload.route || '').toUpperCase();
      const reason = evidence.controlling_reason || firstReason(payload) || 'deterministic policy';
      if (route === 'ANSWER') {
        return `The request stayed inside customer scope and verified records supported a bounded answer. Control: ${reason}.`;
      }
      if (route === 'CLARIFY') {
        return `The system preserved ambiguity instead of guessing. Control: ${reason}.`;
      }
      if (route === 'ESCALATE') {
        return `The request required human review; no fraud conclusion is made by the system. Control: ${reason}.`;
      }
      if (route === 'ABSTAIN') {
        return `The requested action is outside permitted support authority, so no banking action is invoked. Control: ${reason}.`;
      }
      return `The interlock retained deterministic policy authority. Control: ${reason}.`;
    }

    function renderCustomers(customers) {
      state.customers = customers || [];
      els.customerSelect.innerHTML = '';
      if (!state.customers.length) {
        els.customerSelect.innerHTML = '<option value="">No customers found</option>';
        els.startSession.disabled = true;
        return;
      }
      for (const customer of state.customers) {
        const option = document.createElement('option');
        option.value = customer.customer_id;
        option.textContent = `${customer.customer_id} · ${customer.country || 'country n/a'} · ${customer.default_language?.toUpperCase() || 'lang n/a'} · ${customer.transcript_count} messages`;
        els.customerSelect.appendChild(option);
      }
      els.startSession.disabled = false;
    }

    function renderMessages(messages) {
      state.messages = messages || [];
      els.messageSelect.innerHTML = '';
      if (!state.messages.length) {
        els.messageSelect.innerHTML = '<option value="">No provided messages</option>';
        els.useMessage.disabled = true;
        return;
      }
      for (const message of state.messages) {
        const option = document.createElement('option');
        option.value = message.transcript_id;
        option.textContent = `${message.process_date || 'date n/a'} · ${message.detected_language || 'lang n/a'} · ${(message.main_topics || 'topic n/a').slice(0, 60)}`;
        els.messageSelect.appendChild(option);
      }
      els.useMessage.disabled = false;
    }

    async function searchCustomers() {
      showError('');
      const query = els.customerQuery.value.trim();
      const params = new URLSearchParams({ query, limit: '20' });
      const customers = await requestJson(`/api/challenge/customers?${params.toString()}`, { method: 'GET' });
      renderCustomers(customers);
      if (customers.length) await loadMessages();
    }

    async function loadMessages() {
      const customerId = els.customerSelect.value;
      if (!customerId) {
        renderMessages([]);
        return;
      }
      const params = new URLSearchParams({ limit: '25', offset: '0' });
      const messages = await requestJson(`/api/challenge/customers/${encodeURIComponent(customerId)}/messages?${params.toString()}`, { method: 'GET' });
      renderMessages(messages);
    }

    function useSelectedMessage() {
      const selected = state.messages.find((message) => message.transcript_id === els.messageSelect.value);
      if (selected) els.message.value = selected.customer_text;
    }

    async function startSession() {
      showError('');
      const customerId = els.customerSelect.value;
      if (!customerId) throw new Error('Select a customer first.');
      const session = await requestJson('/api/challenge/sessions', {
        method: 'POST',
        body: JSON.stringify({ customer_id: customerId })
      });
      state.session = session;
      els.sessionInfo.innerHTML =
        `Scoped to <strong>${escapeHtml(session.customer_id)}</strong><br>` +
        `Language fallback: ${escapeHtml(String(session.language).toUpperCase())}<br>` +
        `Transcripts: ${escapeHtml(session.transcript_count)}<br>` +
        `Full challenge data: ${escapeHtml(!session.synthetic_data)}`;
      setInitialBoard();
      setControlsDisabled(false);
    }

    async function sendMessage() {
      if (!state.session) throw new Error('Start a scoped customer session first.');
      const message = els.message.value.trim();
      if (!message) throw new Error('Enter or select a message first.');
      setProcessing();
      try {
        const payload = await requestJson('/api/customer/turn', {
          method: 'POST',
          headers: { 'X-Demo-Session': state.session.session_id },
          body: JSON.stringify({ message })
        });
        setRouteBoard(payload);
      } finally {
        setControlsDisabled(false);
      }
    }

    async function humanReview() {
      if (!state.session) throw new Error('Start a scoped customer session first.');
      setProcessing();
      try {
        const payload = await requestJson('/api/customer/handoff', {
          method: 'POST',
          headers: { 'X-Demo-Session': state.session.session_id }
        });
        const wrapped = {
          route: 'ESCALATE',
          intent: 'human_review',
          response_text: `Human review registered. Ticket ${payload.ticket_id}. Persisted: ${payload.persisted}. Verified: ${payload.verified}.`,
          reason_codes: ['human_review_requested'],
          decision_evidence: {
            language: state.session.language,
            interpretation_status: 'verified',
            reference_status: 'not_required',
            controlling_reason: 'human_review_requested',
            action: 'create_escalation_ticket',
            execution_status: payload.persisted ? 'completed' : 'not_invoked',
            verification_codes: [
              payload.persisted ? 'escalation_persisted' : 'persistence_not_confirmed',
              payload.verified ? 'escalation_readback_verified' : 'readback_not_confirmed'
            ]
          }
        };
        setRouteBoard(wrapped);
      } finally {
        setControlsDisabled(false);
      }
    }

    async function revokeSession() {
      if (!state.session) return;
      await requestJson('/api/demo/session', {
        method: 'DELETE',
        headers: { 'X-Demo-Session': state.session.session_id }
      });
      state.session = null;
      els.sessionInfo.textContent = 'Session revoked. Start a new scoped customer session to continue.';
      setInitialBoard();
      setControlsDisabled(false);
    }

    async function guarded(action) {
      try {
        showError('');
        await action();
      } catch (error) {
        showError(error.message || String(error));
        setControlsDisabled(false);
      }
    }

    els.searchCustomers.addEventListener('click', () => guarded(searchCustomers));
    els.customerQuery.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') guarded(searchCustomers);
    });
    els.customerSelect.addEventListener('change', () => guarded(loadMessages));
    els.useMessage.addEventListener('click', useSelectedMessage);
    els.startSession.addEventListener('click', () => guarded(startSession));
    els.sendMessage.addEventListener('click', () => guarded(sendMessage));
    els.humanReview.addEventListener('click', () => guarded(humanReview));
    els.revokeSession.addEventListener('click', () => guarded(revokeSession));

    setInitialBoard();
    setControlsDisabled(false);
    guarded(searchCustomers);
  </script>
</body>
</html>'''
    return (
        html.replace("__MODE_BADGE__", mode_badge)
        .replace("__INTERPRETER__", interpreter)
    )
