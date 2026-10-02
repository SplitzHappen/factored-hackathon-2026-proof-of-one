from __future__ import annotations


DEMO_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof of One — Signal Box Demo</title>
  <style>
    :root {
      color-scheme: dark;
      --ink: #f7f2e7;
      --ink-strong: #fff8dc;
      --muted: #b8c0ad;
      --muted-2: #87917f;
      --rail-bg: #111712;
      --panel: #223028;
      --panel-2: #2e3b33;
      --panel-3: #3d493f;
      --cream: #f6f1dd;
      --black: #121612;
      --line: #73806e;
      --line-soft: rgba(246, 241, 221, 0.14);
      --green: #49e28d;
      --green-dim: #1f7f51;
      --yellow: #ffca3a;
      --yellow-dim: #88620c;
      --red: #ff4f46;
      --red-dim: #8f241f;
      --blue: #94b8ff;
      --blue-dim: #355188;
      --violet: #c0a1ff;
      --off: #3b453d;
      --shadow: 0 30px 80px rgba(0, 0, 0, 0.38);
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 18% 12%, rgba(255, 202, 58, 0.15), transparent 28rem),
        radial-gradient(circle at 82% 0%, rgba(73, 226, 141, 0.12), transparent 30rem),
        linear-gradient(145deg, #0b0f0c, #1b241d 48%, #0f1511);
      color: var(--ink);
    }

    button, select, textarea {
      font: inherit;
    }

    button:focus-visible, select:focus-visible, textarea:focus-visible {
      outline: 3px solid var(--yellow);
      outline-offset: 3px;
    }

    .shell {
      width: min(1480px, 100%);
      margin: 0 auto;
      padding: 24px;
    }

    .masthead {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 18px;
    }

    .brand {
      display: grid;
      gap: 14px;
      padding: 22px;
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(246, 241, 221, 0.10), rgba(246, 241, 221, 0.04)),
        var(--panel);
      border: 1px solid rgba(246, 241, 221, 0.20);
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
    }

    .brand:after {
      content: "";
      position: absolute;
      inset: auto -90px -120px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: rgba(255, 202, 58, 0.13);
      filter: blur(10px);
      pointer-events: none;
    }

    .title-mark {
      width: max-content;
      max-width: 100%;
      padding: 8px;
      border-radius: 10px;
      background: var(--black);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.10);
    }

    .title-mark span {
      display: block;
      padding: 10px 18px 7px;
      border: 3px solid var(--cream);
      border-radius: 6px;
      color: var(--cream);
      font-size: clamp(32px, 5vw, 62px);
      line-height: 0.92;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-family: "Arial Narrow", "Roboto Condensed", Impact, sans-serif;
    }

    .brand h1 {
      margin: 0;
      max-width: 900px;
      font-size: clamp(25px, 3.3vw, 44px);
      line-height: 0.98;
      letter-spacing: -0.045em;
    }

    .brand p {
      margin: 0;
      max-width: 78ch;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.55;
    }

    .runtime {
      min-width: 330px;
      display: grid;
      align-content: start;
      gap: 12px;
      padding: 20px;
      border-radius: 28px;
      background: #0e140f;
      border: 1px solid rgba(246, 241, 221, 0.18);
      box-shadow: var(--shadow);
    }

    .runtime h2 {
      margin: 0;
      font-size: 16px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--cream);
    }

    .meter {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--line-soft);
      color: var(--muted);
      font-size: 14px;
    }

    .lamp {
      width: 15px;
      height: 15px;
      border-radius: 50%;
      background: var(--off);
      border: 1px solid rgba(246, 241, 221, 0.18);
      box-shadow: inset 0 0 0 2px rgba(0,0,0,0.24);
    }

    .lamp.on.green { background: var(--green); box-shadow: 0 0 0 2px #102a1a, 0 0 22px rgba(73,226,141,0.6); }
    .lamp.on.yellow { background: var(--yellow); box-shadow: 0 0 0 2px #3b2a05, 0 0 22px rgba(255,202,58,0.58); }
    .lamp.on.red { background: var(--red); box-shadow: 0 0 0 2px #3b0b08, 0 0 22px rgba(255,79,70,0.58); }
    .lamp.on.blue { background: var(--blue); box-shadow: 0 0 0 2px #162543, 0 0 22px rgba(148,184,255,0.58); }
    .lamp.on.violet { background: var(--violet); box-shadow: 0 0 0 2px #271a45, 0 0 22px rgba(192,161,255,0.58); }

    .meter b {
      color: var(--ink-strong);
      font-weight: 800;
      font-family: var(--mono);
      text-align: right;
      word-break: break-word;
    }

    .workbench {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr) 360px;
      gap: 18px;
      align-items: start;
    }

    .card {
      border-radius: 28px;
      background: rgba(34, 48, 40, 0.92);
      border: 1px solid rgba(246, 241, 221, 0.16);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 16px 18px;
      background: rgba(0,0,0,0.22);
      border-bottom: 1px solid var(--line-soft);
    }

    .card-head h2 {
      margin: 0;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--cream);
    }

    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 26px;
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(246, 241, 221, 0.10);
      color: var(--cream);
      border: 1px solid rgba(246, 241, 221, 0.15);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .tag.answer { background: rgba(73, 226, 141, 0.14); color: #bfffd7; border-color: rgba(73,226,141,0.34); }
    .tag.clarify { background: rgba(255, 202, 58, 0.15); color: #ffe499; border-color: rgba(255,202,58,0.38); }
    .tag.escalate { background: rgba(255, 79, 70, 0.14); color: #ffc1bd; border-color: rgba(255,79,70,0.38); }
    .tag.abstain { background: rgba(148, 184, 255, 0.14); color: #c7d8ff; border-color: rgba(148,184,255,0.38); }
    .tag.handoff { background: rgba(192, 161, 255, 0.14); color: #ded1ff; border-color: rgba(192,161,255,0.38); }

    .console {
      padding: 18px;
      display: grid;
      gap: 14px;
    }

    .field {
      display: grid;
      gap: 7px;
    }

    label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.11em;
      font-weight: 900;
    }

    select, textarea {
      width: 100%;
      border-radius: 16px;
      border: 1px solid rgba(246, 241, 221, 0.18);
      background: #0e140f;
      color: var(--ink);
      padding: 12px;
    }

    textarea {
      min-height: 118px;
      resize: vertical;
      line-height: 1.5;
    }

    .btn {
      width: 100%;
      min-height: 44px;
      border: 0;
      border-radius: 16px;
      cursor: pointer;
      background: var(--cream);
      color: var(--black);
      font-weight: 900;
      letter-spacing: -0.01em;
      box-shadow: 0 12px 28px rgba(0,0,0,0.25);
    }

    .btn:hover:not(:disabled) { filter: brightness(1.06); transform: translateY(-1px); }
    .btn:disabled { opacity: 0.44; cursor: not-allowed; transform: none; }

    .btn.secondary {
      background: #263229;
      color: var(--ink);
      border: 1px solid rgba(246, 241, 221, 0.18);
      box-shadow: none;
    }

    .scenario-grid {
      display: grid;
      gap: 10px;
    }

    .scenario {
      width: 100%;
      text-align: left;
      padding: 12px;
      border-radius: 18px;
      border: 1px solid rgba(246, 241, 221, 0.15);
      background: #182119;
      color: var(--ink);
      cursor: pointer;
    }

    .scenario:hover {
      border-color: rgba(255,202,58,0.50);
      background: #202c22;
    }

    .scenario strong {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      font-size: 14px;
    }

    .scenario small {
      display: block;
      margin-top: 5px;
      color: var(--muted);
      line-height: 1.38;
      font-size: 12px;
    }

    .session {
      padding: 12px;
      border-radius: 18px;
      background: rgba(0,0,0,0.22);
      border: 1px solid var(--line-soft);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      word-break: break-word;
    }

    .session b { color: var(--cream); }

    .error {
      color: #ffd0cc;
      background: rgba(255,79,70,0.12);
      border: 1px solid rgba(255,79,70,0.35);
      border-radius: 16px;
      padding: 12px;
      font-size: 13px;
      line-height: 1.42;
    }

    .signal-panel {
      position: relative;
      min-height: 430px;
      padding: 18px;
      background:
        linear-gradient(135deg, rgba(246,241,221,0.08), rgba(246,241,221,0.03)),
        #c3cbbd;
      color: #171c17;
    }

    .panel-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }

    .line-title {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .panel-label {
      padding: 4px 8px;
      border-radius: 8px;
      background: #20231f;
      color: var(--cream);
      font-weight: 900;
      letter-spacing: 0.08em;
      font-size: 12px;
      text-transform: uppercase;
    }

    .live-note {
      color: #3e493d;
      font-size: 13px;
      line-height: 1.35;
      max-width: 70ch;
    }

    .track {
      position: relative;
      display: grid;
      grid-template-columns: 120px repeat(8, minmax(64px, 1fr)) 138px;
      gap: 8px;
      align-items: center;
      margin: 18px 0 10px;
    }

    .track:before {
      content: "";
      position: absolute;
      left: 50px;
      right: 70px;
      top: 50%;
      height: 6px;
      transform: translateY(-50%);
      border-radius: 999px;
      background: linear-gradient(90deg, #415047, #20231f);
      opacity: 0.88;
    }

    .station, .check, .platform {
      position: relative;
      z-index: 1;
      min-height: 88px;
      border-radius: 18px;
      background: #eef0e4;
      border: 2px solid #6e786b;
      padding: 10px;
      display: grid;
      gap: 6px;
      align-content: start;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.65), 0 10px 20px rgba(0,0,0,0.16);
    }

    .station {
      border-color: #20231f;
      background: #20231f;
      color: var(--cream);
    }

    .station .big {
      font-weight: 900;
      font-family: var(--mono);
      font-size: 22px;
    }

    .check {
      color: #182017;
    }

    .check .num {
      display: flex;
      justify-content: space-between;
      gap: 6px;
      align-items: center;
      font-family: var(--mono);
      font-weight: 900;
      font-size: 13px;
    }

    .check .label {
      font-size: 11px;
      line-height: 1.18;
      color: #394238;
    }

    .check .state {
      display: inline-flex;
      width: max-content;
      max-width: 100%;
      padding: 3px 6px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #20231f;
      background: #d4dacd;
    }

    .check.pass .state { background: #c6f6d8; }
    .check.fire .state { background: #ffd86b; }
    .check.stop .state { background: #ffaaa5; }
    .check.off { opacity: 0.57; }
    .check.off .state { background: #c7ccc0; }

    .mini-lamp {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: inline-block;
      background: #596457;
      box-shadow: inset 0 0 0 2px rgba(0,0,0,0.24);
    }

    .check.pass .mini-lamp { background: var(--green); box-shadow: 0 0 16px rgba(73,226,141,0.66), inset 0 0 0 2px rgba(0,0,0,0.18); }
    .check.fire .mini-lamp { background: var(--yellow); box-shadow: 0 0 16px rgba(255,202,58,0.70), inset 0 0 0 2px rgba(0,0,0,0.18); }
    .check.stop .mini-lamp { background: var(--red); box-shadow: 0 0 16px rgba(255,79,70,0.70), inset 0 0 0 2px rgba(0,0,0,0.18); }

    .platform {
      color: #182017;
      border-color: #20231f;
      background: #ece9da;
      text-align: center;
      align-content: center;
    }

    .platform .route {
      font-family: var(--mono);
      font-size: 16px;
      font-weight: 900;
    }

    .platform .aspect {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      margin: 0 auto;
      background: #596457;
      box-shadow: inset 0 0 0 3px #20231f;
    }

    .platform.on.answer .aspect { background: var(--green); box-shadow: 0 0 0 3px #20231f, 0 0 24px rgba(73,226,141,0.7); }
    .platform.on.clarify .aspect { background: var(--yellow); box-shadow: 0 0 0 3px #20231f, 0 0 24px rgba(255,202,58,0.7); }
    .platform.on.escalate .aspect { background: var(--red); box-shadow: 0 0 0 3px #20231f, 0 0 24px rgba(255,79,70,0.7); }
    .platform.on.abstain .aspect { background: var(--blue); box-shadow: 0 0 0 3px #20231f, 0 0 24px rgba(148,184,255,0.7); }
    .platform.on.handoff .aspect { background: var(--violet); box-shadow: 0 0 0 3px #20231f, 0 0 24px rgba(192,161,255,0.7); }

    .platform-row {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-top: 18px;
    }

    .platform-row .platform {
      min-height: 96px;
    }

    .panel-footer {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, 0.45fr);
      gap: 12px;
      margin-top: 16px;
    }

    .register, .why {
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.42);
      border: 1px solid rgba(32,35,31,0.18);
      color: #20231f;
    }

    .register h3, .why h3 {
      margin: 0 0 8px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #4f5b4b;
    }

    .register p, .why p {
      margin: 0;
      line-height: 1.42;
      font-size: 13px;
    }

    .conversation {
      display: grid;
      gap: 14px;
      padding: 18px;
      background: #111712;
    }

    .message-card {
      display: grid;
      gap: 12px;
      border-radius: 22px;
      border: 1px solid var(--line-soft);
      background: rgba(246,241,221,0.06);
      padding: 16px;
    }

    .msg-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.11em;
      font-weight: 900;
    }

    .message-card .text {
      margin: 0;
      line-height: 1.55;
      font-size: 15px;
    }

    .reply {
      color: var(--cream);
      font-size: 18px;
      font-weight: 800;
      line-height: 1.45;
    }

    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }

    .evidence {
      border-radius: 16px;
      padding: 12px;
      background: rgba(0,0,0,0.22);
      border: 1px solid var(--line-soft);
    }

    .evidence span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 900;
      margin-bottom: 5px;
    }

    .evidence b {
      color: var(--cream);
      font-size: 13px;
      word-break: break-word;
    }

    .record-list {
      display: grid;
      gap: 10px;
    }

    .record {
      border: 1px solid var(--line-soft);
      border-radius: 18px;
      padding: 12px;
      background: rgba(0,0,0,0.18);
    }

    .record strong {
      display: block;
      margin-bottom: 8px;
      color: var(--cream);
    }

    .record dl {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }

    .record dt { color: var(--muted); }
    .record dd { margin: 0; text-align: right; color: var(--ink); }

    .decision {
      padding: 18px;
      display: grid;
      gap: 14px;
    }

    .route-aspect {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 14px;
      align-items: center;
      padding: 14px;
      border-radius: 22px;
      background: rgba(0,0,0,0.20);
      border: 1px solid var(--line-soft);
    }

    .big-aspect {
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: var(--off);
      box-shadow: inset 0 0 0 5px rgba(0,0,0,0.35);
    }

    .big-aspect.answer { background: var(--green); box-shadow: 0 0 0 5px #0b180f, 0 0 34px rgba(73,226,141,0.62); }
    .big-aspect.clarify { background: var(--yellow); box-shadow: 0 0 0 5px #251c05, 0 0 34px rgba(255,202,58,0.62); }
    .big-aspect.escalate { background: var(--red); box-shadow: 0 0 0 5px #250706, 0 0 34px rgba(255,79,70,0.62); }
    .big-aspect.abstain { background: var(--blue); box-shadow: 0 0 0 5px #0c1528, 0 0 34px rgba(148,184,255,0.62); }
    .big-aspect.handoff { background: var(--violet); box-shadow: 0 0 0 5px #1c1231, 0 0 34px rgba(192,161,255,0.62); }

    .route-aspect h3 {
      margin: 0;
      font-family: var(--mono);
      font-size: 26px;
      letter-spacing: -0.04em;
    }

    .route-aspect p {
      margin: 4px 0 0;
      color: var(--muted);
      line-height: 1.35;
      font-size: 13px;
    }

    .limits {
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 20px;
      border: 1px solid rgba(255,202,58,0.32);
      background: rgba(255,202,58,0.08);
      color: #ffe7a4;
      line-height: 1.48;
      font-size: 13px;
    }

    .empty {
      padding: 34px;
      border-radius: 22px;
      border: 1px dashed var(--line-soft);
      color: var(--muted);
      text-align: center;
      line-height: 1.5;
    }

    @media (max-width: 1180px) {
      .masthead, .workbench, .panel-footer { grid-template-columns: 1fr; }
      .runtime { min-width: 0; }
      .track { grid-template-columns: 1fr; }
      .track:before { display: none; }
      .platform-row { grid-template-columns: 1fr 1fr; }
    }

    @media (max-width: 720px) {
      .shell { padding: 14px; }
      .platform-row { grid-template-columns: 1fr; }
      .title-mark span { font-size: 32px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="masthead" aria-label="Proof of One overview">
      <div class="brand">
        <div class="title-mark"><span>Proof of One</span></div>
        <h1>Signal-box routing for bilingual payment support.</h1>
        <p>
          A judge-facing visual prototype over the local synthetic API. Spanish and Portuguese messages enter the same fixed check sequence; the backend sets a route to ANSWER, CLARIFY, ABSTAIN, ESCALATE, or HANDOFF.
        </p>
      </div>

      <aside class="runtime" aria-label="Runtime status">
        <h2>Local readiness ledger</h2>
        <div class="meter"><i class="lamp" id="lamp-ready"></i><span>API status</span><b id="ready-status">checking</b></div>
        <div class="meter"><i class="lamp" id="lamp-data"></i><span>Data mode</span><b id="data-mode">checking</b></div>
        <div class="meter"><i class="lamp" id="lamp-bank"></i><span>Bank/runtime</span><b id="bank-runtime">checking</b></div>
        <div class="meter"><i class="lamp" id="lamp-llm"></i><span>Live LLM</span><b id="llm-connected">checking</b></div>
      </aside>
    </section>

    <section class="workbench">
      <aside class="card">
        <div class="card-head">
          <h2>Signal console</h2>
          <span class="tag">local API</span>
        </div>
        <div class="console">
          <div class="field">
            <label for="persona">Customer line</label>
            <select id="persona"></select>
          </div>

          <div class="field">
            <label for="language">Language lever</label>
            <select id="language">
              <option value="">Use persona default</option>
              <option value="es">Spanish</option>
              <option value="pt">Portuguese</option>
            </select>
          </div>

          <button class="btn" id="start-session">Start synthetic session</button>
          <button class="btn secondary" id="handoff" disabled>Handoff lane · create support ticket</button>
          <button class="btn secondary" id="revoke" disabled>Clear session</button>

          <div class="session" id="session-box">No active session.</div>
          <div class="error" id="error-box" hidden></div>

          <div class="scenario-grid" aria-label="Demo scenarios">
            <label>Scenario buttons</label>
            <button class="scenario" data-persona="lucia" data-message="¿Cuál es el estado de la transacción DEMO-ES-1001?">
              <strong>Known transaction <span class="tag answer">ANSWER</span></strong>
              <small>Spanish support over one verified synthetic transaction.</small>
            </button>
            <button class="scenario" data-persona="lucia" data-message="Quiero consultar una transacción por 54000 COP.">
              <strong>Two possible matches <span class="tag clarify">CLARIFY</span></strong>
              <small>The amount maps to two verified candidates; the backend asks for an exact reference.</small>
            </button>
            <button class="scenario" data-persona="lucia" data-message="No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.">
              <strong>Customer-reported unauthorized activity <span class="tag escalate">ESCALATE</span></strong>
              <small>Routes to human review in the demo. This is not fraud detection.</small>
            </button>
            <button class="scenario" data-persona="lucia" data-message="Quiero transferir dinero a otra cuenta.">
              <strong>Unsupported banking action <span class="tag abstain">ABSTAIN</span></strong>
              <small>Unsupported intent; the backend refuses to invent an answer.</small>
            </button>
            <button class="scenario" data-persona="rafael" data-message="Quero consultar a transação DEMO-PT-2003.">
              <strong>Portuguese transaction path <span class="tag answer">PT</span></strong>
              <small>Rafael’s synthetic account, Portuguese output.</small>
            </button>
          </div>
        </div>
      </aside>

      <section class="card" aria-label="Signal box and conversation">
        <div class="card-head">
          <h2>Interlocking panel</h2>
          <span class="tag" id="active-line">no route set</span>
        </div>
        <div class="signal-panel">
          <div class="panel-top">
            <div>
              <div class="line-title">
                <span class="panel-label" id="line-label">WAITING</span>
                <span class="panel-label" id="route-label">NO ROUTE</span>
                <span class="panel-label" id="intent-label">NO INTENT</span>
              </div>
              <p class="live-note" id="live-note">Start a synthetic session, choose a scenario, and send the message. Lit lamps are computed from the API response.</p>
            </div>
            <span class="panel-label">visual prototype</span>
          </div>

          <div class="track" id="check-track"></div>

          <div class="platform-row" id="platform-row"></div>

          <div class="panel-footer">
            <div class="register">
              <h3>Turn register</h3>
              <p id="turn-register">No message has been sent yet.</p>
            </div>
            <div class="why">
              <h3>Why this route</h3>
              <p id="why-route">The route explanation will appear after the backend responds.</p>
            </div>
          </div>
        </div>

        <div class="conversation">
          <div class="field">
            <label for="message">Customer message</label>
            <textarea id="message" placeholder="Start a session, choose a scenario, then send…"></textarea>
          </div>
          <button class="btn" id="send" disabled>Send through fixed checks</button>
          <div id="conversation-list" class="empty">No turns yet. The first API response will populate the register and evidence cards.</div>
        </div>
      </section>

      <aside class="card">
        <div class="card-head">
          <h2>Decision evidence</h2>
          <span class="tag">API fields</span>
        </div>
        <div class="decision">
          <div class="route-aspect">
            <span class="big-aspect" id="big-aspect"></span>
            <div>
              <h3 id="decision-route">NO ROUTE</h3>
              <p id="decision-summary">Waiting for backend response.</p>
            </div>
          </div>

          <div class="evidence-grid" id="evidence-grid"></div>

          <div class="limits">
            <strong>Boundaries:</strong> synthetic local demo only · visual prototype over existing API · no production or pilot readiness claim · no live-provider claim · no held-out validation claim · no final submission/go-live approval · IPA-M1 remains open.
          </div>
        </div>
      </aside>
    </section>
  </main>

  <script>
    const CHECKS = [
      {n: 1, label: 'Customer-reported unauthorized activity?', reasons: ['unauthorized_activity_reported'], route: 'ESCALATE'},
      {n: 2, label: 'Possible unauthorized activity fail-safe?', reasons: ['possible_unauthorized_activity'], route: 'ESCALATE'},
      {n: 3, label: 'Interpreter unavailable?', reasons: ['interpretation_unavailable', 'interpreter_unavailable'], route: 'ESCALATE'},
      {n: 4, label: 'Conflict, excluded relationship, or unsafe record?', reasons: ['data_conflict', 'relationship_excluded', 'cross_customer_non_disclosure'], route: 'ESCALATE'},
      {n: 5, label: 'Decline explanation request?', reasons: ['decline_reason_unavailable'], route: 'ABSTAIN'},
      {n: 6, label: 'Prohibited banking action?', reasons: ['prohibited_action'], route: 'ABSTAIN'},
      {n: 7, label: 'Unsupported intent?', reasons: ['unsupported_intent'], route: 'ABSTAIN'},
      {n: 8, label: 'Ambiguous, missing, or incomplete reference?', reasons: ['ambiguous_transaction_match', 'missing_required_parameter', 'unverified_record'], route: 'CLARIFY'}
    ];

    const ROUTES = [
      {route: 'ANSWER', className: 'answer', sub: 'Verified answer'},
      {route: 'CLARIFY', className: 'clarify', sub: 'Needs exact reference'},
      {route: 'ABSTAIN', className: 'abstain', sub: 'Unsupported / unsafe'},
      {route: 'ESCALATE', className: 'escalate', sub: 'Human review'},
      {route: 'HANDOFF', className: 'handoff', sub: 'Support ticket'}
    ];

    const state = {
      personas: [],
      session: null,
      turns: [],
      latest: null
    };

    const els = {
      readyStatus: document.getElementById('ready-status'),
      dataMode: document.getElementById('data-mode'),
      bankRuntime: document.getElementById('bank-runtime'),
      llmConnected: document.getElementById('llm-connected'),
      lampReady: document.getElementById('lamp-ready'),
      lampData: document.getElementById('lamp-data'),
      lampBank: document.getElementById('lamp-bank'),
      lampLlm: document.getElementById('lamp-llm'),
      persona: document.getElementById('persona'),
      language: document.getElementById('language'),
      start: document.getElementById('start-session'),
      handoff: document.getElementById('handoff'),
      revoke: document.getElementById('revoke'),
      sessionBox: document.getElementById('session-box'),
      error: document.getElementById('error-box'),
      message: document.getElementById('message'),
      send: document.getElementById('send'),
      checkTrack: document.getElementById('check-track'),
      platformRow: document.getElementById('platform-row'),
      lineLabel: document.getElementById('line-label'),
      routeLabel: document.getElementById('route-label'),
      intentLabel: document.getElementById('intent-label'),
      activeLine: document.getElementById('active-line'),
      liveNote: document.getElementById('live-note'),
      turnRegister: document.getElementById('turn-register'),
      whyRoute: document.getElementById('why-route'),
      conversationList: document.getElementById('conversation-list'),
      bigAspect: document.getElementById('big-aspect'),
      decisionRoute: document.getElementById('decision-route'),
      decisionSummary: document.getElementById('decision-summary'),
      evidenceGrid: document.getElementById('evidence-grid')
    };

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function setError(message) {
      els.error.hidden = !message;
      els.error.textContent = message || '';
    }

    function setLamp(el, on, className) {
      el.className = `lamp${on ? ' on ' + className : ''}`;
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

    function currentLanguage() {
      if (state.session?.language) return state.session.language;
      const selected = state.personas.find((p) => p.persona_id === els.persona.value);
      return els.language.value || selected?.default_language || 'es';
    }

    function routeClass(route) {
      const value = String(route || '').toLowerCase();
      if (['answer', 'clarify', 'abstain', 'escalate', 'handoff'].includes(value)) return value;
      return '';
    }

    function firedCheck(response) {
      if (!response || response.route === 'HANDOFF') return null;
      const reasons = response.reason_codes || [];
      for (const check of CHECKS) {
        if (check.reasons.some((reason) => reasons.includes(reason))) return check;
      }
      return null;
    }

    function checkState(check, response) {
      if (!response || response.route === 'HANDOFF') return 'off';
      const fired = firedCheck(response);
      if (!fired) return response.route === 'ANSWER' ? 'pass' : 'off';
      if (check.n < fired.n) return 'pass';
      if (check.n === fired.n) return fired.route === 'ESCALATE' ? 'stop' : 'fire';
      return 'off';
    }

    function routeSummary(response) {
      if (!response) return 'Waiting for backend response.';
      const route = response.route;
      const reasons = response.reason_codes || [];
      if (route === 'ANSWER') return 'Verified synthetic records supported a bounded answer.';
      if (route === 'CLARIFY') return 'More than one verified candidate matched; the system asks for an exact reference.';
      if (route === 'ABSTAIN') return 'The request is unsupported or unsafe for this demo, so no answer is invented.';
      if (route === 'ESCALATE') {
        if (reasons.includes('unauthorized_activity_reported') || reasons.includes('possible_unauthorized_activity')) {
          return 'The customer reported unauthorized activity, so the demo routes to human review. This is not fraud detection.';
        }
        return 'A safety check routed the request to human review instead of answering automatically.';
      }
      if (route === 'HANDOFF') return 'The explicit support handoff endpoint created a ticket and returned persistence evidence.';
      return 'Backend response received.';
    }

    function routeMeaning(route) {
      if (route === 'ANSWER') return 'answer returned';
      if (route === 'CLARIFY') return 'clarification required';
      if (route === 'ABSTAIN') return 'unsupported request';
      if (route === 'ESCALATE') return 'human review in demo';
      if (route === 'HANDOFF') return 'support ticket created';
      return 'no route set';
    }

    function localeForCurrency(currency) {
      if (currency === 'COP') return 'es-CO';
      if (currency === 'BRL') return 'pt-BR';
      return undefined;
    }

    function formatMoney(value, currency) {
      if (value === undefined || value === null) return '—';
      const numeric = Number(value);
      if (Number.isNaN(numeric)) return `${value} ${currency || ''}`.trim();
      try {
        return new Intl.NumberFormat(localeForCurrency(currency), {
          style: 'currency',
          currency: currency || 'USD',
          currencyDisplay: 'code'
        }).format(numeric).replace(/\u00a0/g, ' ');
      } catch (error) {
        return `${numeric.toLocaleString()} ${currency || ''}`.trim();
      }
    }

    function formatTimestamp(value) {
      if (!value) return '—';
      return String(value).replace('T', ' ').slice(0, 16);
    }

    function renderCheckTrack(response) {
      const lang = currentLanguage();
      const route = response?.route || '';
      const stationLabel = route === 'HANDOFF'
        ? 'HANDOFF'
        : (lang === 'pt' ? 'PT LINE' : 'ES LINE');
      const stationSub = route === 'HANDOFF'
        ? 'separate support lane'
        : 'interpreter → fixed checks';

      const station = `
        <div class="station">
          <span class="big">${escapeHtml(stationLabel)}</span>
          <span>${escapeHtml(stationSub)}</span>
        </div>`;

      const checks = CHECKS.map((check) => {
        const stateName = checkState(check, response);
        const label = stateName === 'pass' ? 'PASS' : stateName === 'fire' ? 'FIRES' : stateName === 'stop' ? 'STOP' : 'OFF';
        return `
          <div class="check ${stateName}">
            <div class="num"><span>${check.n}</span><span class="mini-lamp"></span></div>
            <div class="label">${escapeHtml(check.label)}</div>
            <span class="state">${label}</span>
          </div>`;
      }).join('');

      const platform = `
        <div class="platform ${route ? 'on ' + routeClass(route) : ''}">
          <div class="aspect"></div>
          <div class="route">${escapeHtml(route || 'WAIT')}</div>
          <small>${escapeHtml(routeMeaning(route))}</small>
        </div>`;

      els.checkTrack.innerHTML = station + checks + platform;
    }

    function renderPlatforms(response) {
      const route = response?.route || '';
      els.platformRow.innerHTML = ROUTES.map((entry) => `
        <div class="platform ${route === entry.route ? 'on ' + entry.className : ''}">
          <div class="aspect"></div>
          <div class="route">${escapeHtml(entry.route)}</div>
          <small>${escapeHtml(entry.sub)}</small>
        </div>`).join('');
    }

    function renderPanel(response) {
      const route = response?.route || 'NO ROUTE';
      const lang = currentLanguage().toUpperCase();
      const intent = response?.intent && response.intent !== 'unknown' ? response.intent : (response?.route === 'HANDOFF' ? 'support_handoff' : 'NO INTENT');

      els.lineLabel.textContent = response?.route === 'HANDOFF' ? 'HANDOFF LANE' : `${lang} LINE`;
      els.routeLabel.textContent = route;
      els.intentLabel.textContent = intent;
      els.activeLine.textContent = response ? `${route} set` : 'no route set';
      els.liveNote.textContent = response
        ? 'Lit lamps are derived from the latest API response. Gray checks did not fire for this message.'
        : 'Start a synthetic session, choose a scenario, and send the message. Lit lamps are computed from the API response.';
      els.turnRegister.textContent = response
        ? `${response.route || 'HANDOFF'} · ${response.intent || 'support_handoff'} · ${(response.reason_codes || []).join(', ') || 'no reason code'}`
        : 'No message has been sent yet.';
      els.whyRoute.textContent = routeSummary(response);

      renderCheckTrack(response);
      renderPlatforms(response);
      renderDecision(response);
    }

    function renderDecision(response) {
      const route = response?.route || 'NO ROUTE';
      const cls = routeClass(route);
      els.bigAspect.className = `big-aspect ${cls}`;
      els.decisionRoute.textContent = route;
      els.decisionSummary.textContent = routeSummary(response);

      if (!response) {
        els.evidenceGrid.innerHTML = `
          <div class="evidence"><span>Status</span><b>Waiting</b></div>
          <div class="evidence"><span>Source</span><b>Local synthetic API</b></div>`;
        return;
      }

      const fields = [
        ['Route', response.route],
        ['Intent', response.intent || 'support_handoff'],
        ['Reason codes', (response.reason_codes || []).join(', ') || 'none returned'],
        ['Synthetic data', response.synthetic_data === true ? 'true' : 'not returned'],
      ];

      if (response.escalation_ticket_id) fields.push(['Ticket ID', response.escalation_ticket_id]);
      if (response.ticket_id) fields.push(['Ticket ID', response.ticket_id]);
      if (response.persisted !== undefined) fields.push(['Persisted', String(response.persisted)]);
      if (response.verified !== undefined) fields.push(['Verified', String(response.verified)]);
      if (response.handoff_available !== undefined) fields.push(['Handoff available', String(response.handoff_available)]);
      if (response.clarification_transaction_ids?.length) fields.push(['Candidates', response.clarification_transaction_ids.join(', ')]);

      els.evidenceGrid.innerHTML = fields.map(([label, value]) => `
        <div class="evidence"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`).join('');
    }

    function renderRecord(record) {
      return `
        <div class="record">
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
        </div>`;
    }

    function renderConversation() {
      if (!state.turns.length) {
        els.conversationList.className = 'empty';
        els.conversationList.textContent = 'No turns yet. The first API response will populate the register and evidence cards.';
        return;
      }
      els.conversationList.className = 'record-list';
      els.conversationList.innerHTML = state.turns.map((turn) => {
        const response = turn.response || {};
        const records = [...(response.products || []), ...(response.transactions || [])];
        const candidates = response.clarification_transaction_ids || [];
        return `
          <article class="message-card">
            <div>
              <div class="msg-label">Customer</div>
              <p class="text">${escapeHtml(turn.message || 'Explicit support handoff requested')}</p>
            </div>
            <div>
              <div class="msg-label">System response</div>
              <p class="text reply">${escapeHtml(response.response_text || turn.text || '')}</p>
            </div>
            <div class="tag ${routeClass(response.route)}">${escapeHtml(response.route || 'EVENT')}</div>
            <p class="text">${escapeHtml(routeSummary(response))}</p>
            ${response.reason_codes?.length ? `<div>${response.reason_codes.map((code) => `<span class="tag">${escapeHtml(code)}</span>`).join(' ')}</div>` : ''}
            ${candidates.length ? `<div class="record"><strong>Clarification candidates</strong><p class="text">${candidates.map(escapeHtml).join(', ')}</p></div>` : ''}
            ${records.length ? `<div class="record-list">${records.map(renderRecord).join('')}</div>` : ''}
          </article>`;
      }).join('');
    }

    function renderSession() {
      if (!state.session) {
        els.sessionBox.textContent = 'No active session.';
        els.send.disabled = true;
        els.handoff.disabled = true;
        els.revoke.disabled = true;
        return;
      }
      els.sessionBox.innerHTML = `
        <b>${escapeHtml(state.session.display_name)}</b><br>
        Session: ${escapeHtml(state.session.session_id)}<br>
        Tenant: ${escapeHtml(state.session.tenant_id)}<br>
        Role: ${escapeHtml(state.session.role)}<br>
        Language: ${escapeHtml(state.session.language)}<br>
        Synthetic data: ${escapeHtml(state.session.synthetic_data)}`;
      els.send.disabled = false;
      els.handoff.disabled = false;
      els.revoke.disabled = false;
    }

    async function loadReady() {
      try {
        const ready = await api('/ready', {headers: {}});
        els.readyStatus.textContent = ready.status;
        els.dataMode.textContent = ready.data_mode || 'unknown';
        els.bankRuntime.textContent = `${ready.bank_ready}/${ready.runtime_ready}`;
        els.llmConnected.textContent = String(ready.llm_connected);
        setLamp(els.lampReady, ready.status === 'ready', 'green');
        setLamp(els.lampData, ready.synthetic_data === true, 'green');
        setLamp(els.lampBank, ready.bank_ready && ready.runtime_ready, 'green');
        setLamp(els.lampLlm, ready.llm_connected === false, 'yellow');
      } catch (error) {
        els.readyStatus.textContent = 'not_ready';
        els.dataMode.textContent = 'unknown';
        els.bankRuntime.textContent = 'false/false';
        setLamp(els.lampReady, false, 'red');
      }
    }

    async function loadPersonas() {
      state.personas = await api('/api/demo/personas', {headers: {}});
      els.persona.innerHTML = state.personas.map((persona) => (
        `<option value="${escapeHtml(persona.persona_id)}">${escapeHtml(persona.display_name)} · ${escapeHtml(persona.default_language.toUpperCase())}</option>`
      )).join('');
    }

    async function startSession() {
      setError('');
      const body = {persona_id: els.persona.value};
      if (els.language.value) body.language = els.language.value;
      state.session = await api('/api/demo/sessions', {
        method: 'POST',
        headers: {},
        body: JSON.stringify(body)
      });
      state.turns = [];
      state.latest = null;
      renderSession();
      renderConversation();
      renderPanel(null);
    }

    async function sendTurn() {
      setError('');
      const message = els.message.value.trim();
      if (!message) return;
      if (state.session && els.persona.value !== state.session.persona_id) {
        setError('The selected customer line differs from the active session. Start a new synthetic session before sending.');
        return;
      }
      const response = await api('/api/customer/turn', {
        method: 'POST',
        body: JSON.stringify({message})
      });
      state.latest = response;
      state.turns.unshift({message, response});
      renderPanel(response);
      renderConversation();
    }

    async function requestHandoff() {
      setError('');
      const response = await api('/api/customer/handoff', {method: 'POST', body: '{}'});
      const handoffText = response.persisted && response.verified
        ? `Support ticket created and verified. Ticket: ${response.ticket_id}`
        : `Support ticket response received. Ticket: ${response.ticket_id || 'not returned'}`;
      const wrapped = {
        route: 'HANDOFF',
        intent: 'customer_requested_support_handoff',
        response_text: handoffText,
        reason_codes: [],
        synthetic_data: state.session?.synthetic_data === true,
        ticket_id: response.ticket_id,
        persisted: response.persisted,
        verified: response.verified,
        session_id: response.session_id
      };
      state.latest = wrapped;
      state.turns.unshift({message: 'Explicit support handoff requested', text: handoffText, response: wrapped});
      renderPanel(wrapped);
      renderConversation();
    }

    async function revokeSession() {
      setError('');
      await api('/api/demo/session', {method: 'DELETE', body: '{}'});
      state.session = null;
      state.turns = [];
      state.latest = null;
      renderSession();
      renderConversation();
      renderPanel(null);
    }

    els.start.addEventListener('click', () => startSession().catch((error) => setError(error.message)));
    els.send.addEventListener('click', () => sendTurn().catch((error) => setError(error.message)));
    els.handoff.addEventListener('click', () => requestHandoff().catch((error) => setError(error.message)));
    els.revoke.addEventListener('click', () => revokeSession().catch((error) => setError(error.message)));

    document.querySelectorAll('.scenario').forEach((button) => {
      button.addEventListener('click', () => {
        els.message.value = button.dataset.message || '';
        if (button.dataset.persona) {
          els.persona.value = button.dataset.persona;
          const persona = state.personas.find((p) => p.persona_id === button.dataset.persona);
          if (persona) els.language.value = '';
        }
      });
    });

    Promise.all([loadReady(), loadPersonas()]).catch((error) => setError(error.message));
    renderSession();
    renderPanel(null);
  </script>
</body>
</html>
"""


def render_demo_ui() -> str:
    """Return the dependency-free judge-facing local demo shell."""

    return DEMO_UI_HTML
