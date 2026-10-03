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
      font-size: clamp(24px, 4vw, 44px);
      line-height: 0.98;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      text-shadow: 0 0 20px rgba(246, 237, 207, 0.18);
    }

    .brand p {
      margin: 0;
      max-width: 900px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.45;
    }

    .route-token {
      justify-self: end;
      min-width: 188px;
      max-width: 280px;
      border: 1px solid rgba(246, 237, 207, 0.25);
      border-radius: 999px;
      padding: 14px 18px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--cream);
      font-size: 19px;
      font-weight: 900;
      letter-spacing: 0.06em;
      line-height: 1.1;
      text-align: center;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .route-token.answer { background: rgba(52, 212, 119, 0.16); border-color: rgba(52, 212, 119, 0.65); }
    .route-token.clarify { background: rgba(255, 209, 92, 0.15); border-color: rgba(255, 209, 92, 0.72); }
    .route-token.abstain { background: rgba(169, 177, 189, 0.13); border-color: rgba(169, 177, 189, 0.62); }
    .route-token.escalate { background: rgba(255, 102, 92, 0.14); border-color: rgba(255, 102, 92, 0.72); }
    .route-token.handoff { background: rgba(187, 140, 255, 0.16); border-color: rgba(187, 140, 255, 0.72); }

    .main {
      display: grid;
      grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
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
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    select, textarea, button {
      width: 100%;
      border-radius: 14px;
      font: inherit;
    }

    select, textarea {
      border: 1px solid rgba(246, 237, 207, 0.25);
      background: rgba(8, 14, 9, 0.72);
      color: var(--cream);
      padding: 12px 13px;
    }

    textarea {
      min-height: 96px;
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
    .handoff-btn { background: rgba(82, 49, 108, 0.72); border-color: rgba(187, 140, 255, 0.55); }
    .revoke { background: rgba(92, 38, 34, 0.72); border-color: rgba(255, 102, 92, 0.55); }

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
      color: #ffd8d5;
      border: 1px solid rgba(255, 102, 92, 0.45);
      background: rgba(255, 102, 92, 0.10);
    }

    .preset-heading {
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .scenario-grid { display: grid; gap: 10px; }

    .scenario {
      text-align: left;
      text-transform: none;
      letter-spacing: 0;
      border-left-width: 6px;
    }

    .scenario small {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-weight: 500;
      line-height: 1.35;
    }

    .scenario.answer { border-left-color: var(--answer); }
    .scenario.clarify { border-left-color: var(--clarify); }
    .scenario.abstain { border-left-color: var(--abstain); }
    .scenario.escalate { border-left-color: var(--escalate); }
    .scenario.pt { border-left-color: var(--handoff); }

    .workbench { display: grid; gap: 18px; }

    .signal-board {
      overflow: hidden;
      padding: 20px;
      color: #1e2d25;
      background:
        linear-gradient(180deg, rgba(224, 229, 211, 0.94), rgba(191, 201, 183, 0.94)),
        radial-gradient(circle at center, rgba(255, 255, 255, 0.30), transparent 30rem);
    }

    .signal-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 18px;
    }

    .signal-copy { min-width: 0; }

    .signal-head h2 {
      margin: 0 0 10px;
      color: #142016;
      font-size: clamp(24px, 3vw, 36px);
      letter-spacing: 0.12em;
      line-height: 1.08;
      text-transform: uppercase;
    }

    .signal-head p {
      margin: 0;
      max-width: 850px;
      color: #35483f;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.45;
    }

    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      min-width: 0;
      max-width: 430px;
    }

    .badge {
      display: inline-flex;
      justify-content: center;
      align-items: center;
      max-width: 210px;
      min-height: 36px;
      border-radius: 999px;
      background: #101610;
      color: var(--cream);
      font-weight: 900;
      font-size: 13px;
      line-height: 1.15;
      letter-spacing: 0.045em;
      overflow: hidden;
      padding: 8px 11px;
      text-align: center;
      text-overflow: ellipsis;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .badge.intent { max-width: 180px; }
    .badge.prototype {
      max-width: none;
      overflow: visible;
      text-overflow: clip;
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
      min-width: 0;
      min-height: 160px;
      display: grid;
      align-content: center;
      gap: 12px;
      overflow: hidden;
      border: 3px solid #1a211b;
      border-radius: 26px;
      background: #101610;
      color: var(--cream);
      padding: 22px;
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

    .check {
      position: relative;
      z-index: 1;
      min-height: 150px;
      display: grid;
      align-content: space-between;
      gap: 10px;
      overflow: hidden;
      border: 3px solid rgba(30, 43, 35, 0.42);
      border-radius: 22px;
      background: rgba(236, 239, 225, 0.96);
      color: #26322a;
      padding: 15px 14px;
    }

    .check.waiting { opacity: 0.72; }
    .check.clear {
      border-color: rgba(27, 127, 74, 0.72);
      background: rgba(231, 242, 226, 0.98);
    }
    .check.on {
      border-color: #141a14;
      box-shadow: 0 0 0 3px rgba(255, 209, 92, 0.25), 0 14px 28px rgba(0, 0, 0, 0.20);
    }
    .check.na {
      opacity: 0.58;
      border-style: dashed;
    }

    .check-head { display: flex; justify-content: space-between; gap: 8px; align-items: start; }
    .check-num { color: #566357; font-size: 22px; font-weight: 900; }

    .lamp {
      flex: 0 0 auto;
      width: 30px;
      height: 30px;
      border: 4px solid #242a24;
      border-radius: 999px;
      background: #596555;
      box-shadow: inset 0 0 0 5px rgba(0, 0, 0, 0.12);
    }

    .check.waiting .lamp { background: var(--waiting); }
    .check.clear .lamp { background: var(--clear); box-shadow: 0 0 0 4px rgba(27, 127, 74, 0.16); }
    .check.on .lamp { background: var(--clarify); box-shadow: 0 0 20px rgba(255, 209, 92, 0.72); }
    .check.na .lamp { background: var(--na); box-shadow: none; }

    .check-title {
      color: #415044;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 14px;
      font-weight: 780;
      line-height: 1.22;
    }

    .check-state {
      justify-self: start;
      border-radius: 999px;
      background: rgba(34, 45, 36, 0.12);
      color: #657160;
      font-size: 13px;
      font-weight: 900;
      letter-spacing: 0.06em;
      padding: 6px 10px;
      text-transform: uppercase;
    }

    .check.waiting .check-state { color: #293129; background: rgba(109, 119, 107, 0.24); }
    .check.clear .check-state { color: #0d4d2b; background: rgba(52, 212, 119, 0.24); }
    .check.on .check-state { color: #161b14; background: rgba(255, 209, 92, 0.72); }
    .check.na .check-state { color: #4f574f; background: rgba(139, 145, 136, 0.24); }

    .platforms {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 12px;
      margin: 16px 0 0;
    }

    .platform {
      min-height: 145px;
      display: grid;
      justify-items: center;
      align-content: center;
      gap: 10px;
      border: 3px solid #181e18;
      border-radius: 26px;
      background: #f0ecd9;
      color: #111711;
      padding: 12px;
      text-align: center;
    }

    .platform.active {
      transform: translateY(-2px);
      background: #121b14;
      color: var(--cream);
      box-shadow: 0 0 0 4px rgba(20, 26, 20, 0.18), 0 20px 40px rgba(0, 0, 0, 0.24);
    }

    .signal-lamp {
      width: 58px;
      height: 58px;
      border: 6px solid #202720;
      border-radius: 999px;
      background: #5b6859;
    }

    .platform.active.answer .signal-lamp { background: var(--answer); box-shadow: 0 0 26px rgba(52, 212, 119, 0.78); }
    .platform.active.clarify .signal-lamp { background: var(--clarify); box-shadow: 0 0 26px rgba(255, 209, 92, 0.78); }
    .platform.active.abstain .signal-lamp { background: var(--abstain); box-shadow: 0 0 24px rgba(169, 177, 189, 0.65); }
    .platform.active.escalate .signal-lamp { background: var(--escalate); box-shadow: 0 0 26px rgba(255, 102, 92, 0.78); }
    .platform.active.handoff .signal-lamp { background: var(--handoff); box-shadow: 0 0 26px rgba(187, 140, 255, 0.78); }

    .platform b { font-size: 22px; letter-spacing: 0.05em; }
    .platform span { font-family: Inter, ui-sans-serif, system-ui, sans-serif; line-height: 1.28; }
    .route-set {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 4px 8px;
      background: var(--cream);
      color: #121b14;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .boundary-strip {
      margin-top: 14px;
      border: 2px solid rgba(20, 32, 22, 0.32);
      border-radius: 14px;
      padding: 10px 12px;
      background: rgba(16, 22, 16, 0.90);
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.35;
      text-align: center;
    }

    .line-summary {
      min-width: 0;
      display: grid;
      gap: 7px;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.35;
    }

    .line-summary span {
      min-width: 0;
      display: block;
      overflow-wrap: anywhere;
      word-break: break-word;
      white-space: normal;
    }

    .line-summary strong { color: var(--cream); }
    .line-boundary {
      margin-top: 2px;
      border-top: 1px solid rgba(246, 237, 207, 0.20);
      padding-top: 8px;
      color: #f7d7b3;
      font-weight: 800;
    }

    .lower-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(310px, 0.95fr);
      gap: 18px;
    }

    .console, .ledger { padding: 20px; min-width: 0; }

    .console h3, .ledger h3 {
      margin: 0 0 12px;
      color: var(--cream);
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .turns { display: grid; gap: 12px; }

    .turn, .why-card, .record {
      border: 1px solid rgba(246, 237, 207, 0.18);
      border-radius: 18px;
      background: rgba(8, 14, 9, 0.58);
      padding: 14px;
    }

    .turn-user {
      margin-bottom: 8px;
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.45;
    }

    .turn-response {
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 16px;
      font-weight: 700;
      line-height: 1.45;
    }

    .why-card {
      min-height: 72px;
      margin-bottom: 18px;
      color: var(--cream);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      line-height: 1.5;
    }

    .kv {
      display: grid;
      gap: 0;
      margin: 0 0 16px;
      border-top: 1px solid rgba(246, 237, 207, 0.12);
    }

    .kv div {
      display: grid;
      grid-template-columns: minmax(108px, 0.42fr) minmax(0, 1fr);
      align-items: start;
      column-gap: 18px;
      min-height: 42px;
      border-bottom: 1px solid rgba(246, 237, 207, 0.12);
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.35;
      padding: 10px 0;
    }

    .kv span {
      min-width: 0;
      padding-top: 1px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.07em;
      text-transform: uppercase;
    }

    .kv b {
      min-width: 0;
      color: var(--cream);
      line-height: 1.35;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; }

    .pill {
      display: inline-flex;
      border: 1px solid rgba(246, 237, 207, 0.16);
      border-radius: 999px;
      background: rgba(246, 237, 207, 0.09);
      color: var(--cream);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      overflow-wrap: anywhere;
      padding: 5px 8px;
      text-transform: uppercase;
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
    .record dd { margin: 0; color: var(--cream); text-align: right; overflow-wrap: anywhere; }

    .limits {
      margin-top: 18px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      font-size: 13px;
      line-height: 1.45;
      padding: 14px 20px 18px;
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
      .badge-row { justify-content: flex-start; max-width: 100%; }
    }

    @media (max-width: 640px) {
      .page { width: 100%; padding: 0; }
      .shell { border-radius: 0; }
      .main { padding: 12px; }
      .controls { grid-template-columns: 1fr; }
      .checks, .platforms { grid-template-columns: 1fr; }
      .kv div { grid-template-columns: 1fr; row-gap: 6px; padding: 11px 0; }
      .kv span { padding-top: 0; }
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
          <button id="revoke" class="revoke" disabled>Revoke session</button>
          <div id="session-box" class="session-box full">No active synthetic session.</div>
          <div id="error-box" class="error full" hidden></div>

          <div class="field full">
            <label for="message">Customer message</label>
            <textarea id="message" placeholder="Choose a scenario, then send to the local API…"></textarea>
          </div>
          <button id="send" disabled class="primary full">Set route · send message</button>

          <div class="full"><div class="preset-heading">Scenario presets</div></div>
          <div class="scenario-grid full" aria-label="demo scenarios">
            <button class="scenario answer" data-persona="lucia" data-message="¿Cuál es el estado de la transacción DEMO-ES-1001?">ANSWER · Known transaction<small>Synthetic record lookup.</small></button>
            <button class="scenario clarify" data-persona="lucia" data-message="Quiero consultar una transacción por 54000 COP.">CLARIFY · Two matches<small>Amount matches more than one synthetic transaction.</small></button>
            <button class="scenario escalate" data-persona="lucia" data-message="No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.">ESCALATE · Unauthorized report<small>Customer-reported issue; not fraud detection.</small></button>
            <button class="scenario abstain" data-persona="lucia" data-message="Quiero hacer una transferencia de 10000 COP a otra cuenta.">ABSTAIN · Out-of-scope request<small>Unsupported intent stays outside the bounded workflow.</small></button>
            <button class="scenario pt" data-persona="rafael" data-message="Qual é o estado da transação DEMO-PT-2001?">PT · Rafael path<small>Portuguese path over synthetic data.</small></button>
          </div>
        </aside>

        <section class="workbench">
          <section class="card signal-board" aria-label="interlocking panel">
            <div class="signal-head">
              <div class="signal-copy">
                <h2>Interlocking · 8 fixed checks</h2>
                <p>Spanish and Portuguese messages pass through the same ordered deterministic guardrail. The first check that fires sets the bounded route.</p>
              </div>
              <div class="badge-row">
                <span id="language-line" class="badge">ES/PT line</span>
                <span id="intent-badge" class="badge intent">No intent</span>
                <span class="badge prototype">Local prototype · synthetic</span>
              </div>
            </div>

            <div class="lines">
              <div class="line-card">
                <b id="active-line">No line</b>
                <div class="line-summary">
                  <span id="line-interpreter"><strong>Interpreter:</strong> awaiting message</span>
                  <span id="line-decision"><strong>Checks:</strong> not evaluated</span>
                  <span id="line-route"><strong>Route:</strong> not set</span>
                  <span id="line-boundary" class="line-boundary">No live LLM · Not fraud detection</span>
                </div>
              </div>
              <div id="checks" class="checks"></div>
            </div>

            <div id="platforms" class="platforms"></div>
            <div class="boundary-strip">Synthetic data · local API · no live LLM · not fraud detection · not production/pilot-ready</div>
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
        Boundary: synthetic demo data only · local API prototype · no production or pilot readiness claim · no live-provider readiness claim · not fraud detection · no final submission/go-live claim.
      </footer>
    </section>
  </main>

  <script>
    const checks = [
      ['unauthorized_activity_reported', 'Customer-reported unauthorized activity?'],
      ['possible_unauthorized_activity', 'Message may report unauthorized activity?'],
      ['interpreter_unavailable', 'Interpreter unavailable?'],
      ['unsafe_or_excluded_record', 'Record conflict, excluded account link, or unsafe record?'],
      ['decline_explanation_request', 'Asks why a payment was declined?'],
      ['prohibited_banking_action', 'Prohibited banking action?'],
      ['unsupported_intent', 'Unsupported intent?'],
      ['ambiguous_transaction_match', 'Multiple verified matches?']
    ];

    const platforms = [
      ['ANSWER', 'Record-backed answer', 'answer'],
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
      intentBadge: document.getElementById('intent-badge'),
      lineInterpreter: document.getElementById('line-interpreter'),
      lineDecision: document.getElementById('line-decision'),
      lineRoute: document.getElementById('line-route'),
      lineBoundary: document.getElementById('line-boundary')
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

    function humanizeCode(value) {
      return String(value || '')
        .replaceAll('_', ' ')
        .replace(/w/g, (char) => char.toUpperCase());
    }

    function displayIntent(intent, reasonCodes = []) {
      const raw = String(intent || '').toLowerCase();
      if ((!raw || raw === 'unknown') && reasonCodes.includes('unsupported_intent')) return 'UNSUPPORTED INTENT';
      if (!raw || raw === 'unknown') return 'AWAITING MESSAGE';
      const labels = {
        transaction_status: 'TX STATUS',
        transaction_lookup: 'TX LOOKUP',
        customer_requested_support_handoff: 'SUPPORT HANDOFF',
        unsupported_intent: 'UNSUPPORTED',
        prohibited_banking_action: 'PROHIBITED',
        unauthorized_activity: 'UNAUTHORIZED'
      };
      if (labels[raw]) return labels[raw];
      const compact = raw.replace(/^customer_requested_/, '').replace(/^transaction_/, 'tx_').replaceAll('_', ' ').toUpperCase();
      return compact.length > 18 ? `${compact.slice(0, 17)}…` : compact;
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
      if (route === 'ANSWER') return 'The backend found a supported request over matched synthetic records for this session.';
      if (route === 'CLARIFY') return 'The backend found more than one matched synthetic record and refused to guess.';
      if (route === 'ESCALATE') return 'The customer reported unauthorized activity; the demo routes to human review. Not fraud detection.';
      if (route === 'ABSTAIN') return 'The request is outside the supported or safe demo boundary, so the system abstains.';
      if (route === 'HANDOFF') return 'The separate handoff endpoint created support-ticket evidence with persisted/verified flags.';
      if (reasons.length) return `Backend returned reason code(s): ${reasons.join(', ')}.`;
      return 'Waiting for backend response.';
    }

    function renderChecks(response) {
      const route = response?.route;
      const reasons = response?.reason_codes || [];
      const firedIndex = checks.findIndex(([code]) => reasons.includes(code));

      els.checks.innerHTML = checks.map(([code, label], index) => {
        let stateName = 'waiting';
        let stateLabel = 'WAITING';

        if (route === 'HANDOFF') {
          stateName = 'na';
          stateLabel = 'N/A';
        } else if (route === 'ANSWER') {
          stateName = 'clear';
          stateLabel = 'CLEAR';
        } else if (route && firedIndex >= 0) {
          if (index < firedIndex) {
            stateName = 'clear';
            stateLabel = 'CLEAR';
          } else if (index === firedIndex) {
            stateName = 'on';
            stateLabel = 'ON';
          } else {
            stateName = 'na';
            stateLabel = 'N/A';
          }
        } else if (route) {
          stateName = 'na';
          stateLabel = 'N/A';
        }

        return `<article class="check ${stateName}">
          <div class="check-head"><span class="check-num">${index + 1}</span><span class="lamp" aria-hidden="true"></span></div>
          <div class="check-title">${escapeHtml(label)}</div>
          <div class="check-state">${stateLabel}</div>
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
          ${active ? '<span class="route-set">▶ Route set</span>' : ''}
        </article>`;
      }).join('');
    }

    function renderLineSummary(response) {
      const route = response?.route;
      const intent = response?.intent && response.intent !== 'unknown' ? response.intent : null;
      const reasons = response?.reason_codes || [];
      const firedIndex = checks.findIndex(([code]) => reasons.includes(code));

      if (!response) {
        els.lineInterpreter.innerHTML = '<strong>Interpreter:</strong> awaiting message';
        els.lineDecision.innerHTML = '<strong>Checks:</strong> not evaluated';
        els.lineRoute.innerHTML = '<strong>Route:</strong> not set';
        els.lineBoundary.textContent = 'No live LLM · Not fraud detection';
        return;
      }

      if (route === 'HANDOFF') {
        els.lineInterpreter.innerHTML = '<strong>Endpoint:</strong> separate support handoff';
        els.lineDecision.innerHTML = `<strong>Evidence:</strong> persisted ${escapeHtml(response.persisted)} · read-back verified ${escapeHtml(response.verified)} · synthetic ${escapeHtml(response.synthetic_data)}`;
        els.lineRoute.innerHTML = '<strong>Checks:</strong> N/A · separate endpoint → HANDOFF';
        els.lineBoundary.textContent = 'No live LLM · Not fraud detection';
        return;
      }

      els.lineInterpreter.innerHTML = `<strong>Interpreter:</strong> deterministic provider · no live LLM${intent ? `<br><strong>Intent:</strong> ${escapeHtml(humanizeCode(intent))}` : ''}`;
      if (route === 'ANSWER') {
        els.lineDecision.innerHTML = '<strong>Checks:</strong> 1–8 CLEAR';
      } else if (firedIndex >= 0) {
        els.lineDecision.innerHTML = `<strong>First fired:</strong> check ${firedIndex + 1}<br><strong>Reason:</strong> ${escapeHtml(humanizeCode(reasons[firedIndex] || reasons[0]))}`;
      } else {
        els.lineDecision.innerHTML = '<strong>Checks:</strong> route returned without a mapped demo check';
      }
      els.lineRoute.innerHTML = `<strong>Route:</strong> ${escapeHtml(route || 'not set')}`;
      els.lineBoundary.textContent = 'Deterministic checks override intent · Not fraud detection';
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
      els.intentBadge.textContent = displayIntent(response?.intent, response?.reason_codes || []);
      els.intentBadge.title = response?.intent || 'Awaiting message';
      els.why.textContent = computeWhy(response);
      renderLineSummary(response);

      const kv = [];
      kv.push(['Route', route]);
      if (response?.intent && response.intent !== 'unknown') kv.push(['Intent', response.intent]);
      if (response?.synthetic_data !== undefined) kv.push(['Synthetic', String(response.synthetic_data)]);
      if (response?.escalation_ticket_id) kv.push(['Ticket', response.escalation_ticket_id]);
      if (response?.ticket_id) kv.push(['Ticket', response.ticket_id]);
      if (response?.persisted !== undefined) kv.push(['Persisted', String(response.persisted)]);
      if (response?.verified !== undefined) kv.push(['Read-back verified', String(response.verified)]);
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
      els.message.value = '';
      const response = await api('/api/customer/handoff', {method: 'POST', body: '{}'});
      const text = response.persisted && response.verified
        ? `Support ticket persisted and read-back verified. Ticket: ${response.ticket_id}`
        : `Support ticket response received. Ticket: ${response.ticket_id || 'not returned'}`;
      const mapped = {
        route: 'HANDOFF',
        intent: 'customer_requested_support_handoff',
        response_text: text,
        ticket_id: response.ticket_id,
        persisted: response.persisted,
        verified: response.verified,
        synthetic_data: state.session?.synthetic_data === true
      };
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
