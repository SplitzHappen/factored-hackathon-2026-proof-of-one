from __future__ import annotations


DEMO_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof of One — Judge Demo</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050816;
      --bg2: #0d1024;
      --panel: rgba(12, 18, 38, 0.78);
      --panel-strong: rgba(16, 24, 49, 0.92);
      --line: rgba(177, 194, 255, 0.18);
      --line-strong: rgba(214, 224, 255, 0.34);
      --text: #f8fbff;
      --muted: #9ba8c6;
      --faint: #687592;
      --cyan: #47e8ff;
      --blue: #6f8cff;
      --violet: #a56bff;
      --pink: #ff5ea8;
      --green: #35e4a6;
      --amber: #ffc857;
      --red: #ff5c7a;
      --slate: #9aa6bd;
      --shadow: 0 30px 90px rgba(0, 0, 0, 0.42);
      --radius-xl: 34px;
      --radius-lg: 24px;
      --radius-md: 16px;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-family: var(--sans);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 4%, rgba(71, 232, 255, 0.25), transparent 30rem),
        radial-gradient(circle at 82% 10%, rgba(165, 107, 255, 0.24), transparent 34rem),
        radial-gradient(circle at 54% 88%, rgba(255, 94, 168, 0.14), transparent 42rem),
        linear-gradient(135deg, #050816 0%, #090d20 46%, #0e1430 100%);
      overflow-x: hidden;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
      background-size: 72px 72px;
      mask-image: radial-gradient(circle at 50% 18%, black, transparent 72%);
    }

    button, select, textarea { font: inherit; }

    .app {
      width: min(1500px, calc(100vw - 40px));
      margin: 0 auto;
      padding: 26px 0 24px;
      position: relative;
    }

    .chrome {
      border: 1px solid var(--line);
      background: linear-gradient(145deg, rgba(9, 14, 32, 0.82), rgba(10, 18, 42, 0.64));
      box-shadow: var(--shadow);
      border-radius: 38px;
      overflow: hidden;
      backdrop-filter: blur(22px);
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 22px;
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.025);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
      min-width: 0;
    }

    .mark {
      width: 44px;
      height: 44px;
      border-radius: 15px;
      display: grid;
      place-items: center;
      color: #03101a;
      font-weight: 950;
      background: conic-gradient(from 210deg, var(--cyan), var(--blue), var(--violet), var(--pink), var(--cyan));
      box-shadow: 0 0 34px rgba(71,232,255,0.25);
    }

    .brand-title { display: grid; gap: 2px; }
    .brand-title strong { font-size: 18px; letter-spacing: -0.02em; }
    .brand-title span { color: var(--muted); font-size: 13px; }

    .limit-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }

    .chip {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.055);
      color: #dbe5ff;
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.02em;
      white-space: nowrap;
    }

    .chip.cyan { color: #c9fbff; border-color: rgba(71,232,255,0.35); }
    .chip.warn { color: #ffedbd; border-color: rgba(255,200,87,0.36); }
    .chip.pink { color: #ffd0e5; border-color: rgba(255,94,168,0.36); }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
      gap: 20px;
      padding: 26px;
    }

    .hero-copy {
      min-height: 430px;
      padding: 34px;
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      background:
        linear-gradient(150deg, rgba(20,31,68,0.92), rgba(10,17,38,0.74)),
        radial-gradient(circle at 20% 10%, rgba(71,232,255,0.22), transparent 26rem);
      position: relative;
      overflow: hidden;
    }

    .hero-copy::after {
      content: "";
      position: absolute;
      inset: auto -100px -140px auto;
      width: 360px;
      height: 360px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,94,168,0.22), transparent 68%);
    }

    .kicker {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: #c9fbff;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 12px;
      font-weight: 950;
    }

    .pulse-dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--green);
      box-shadow: 0 0 18px rgba(53,228,166,0.9);
    }

    h1 {
      max-width: 900px;
      margin: 22px 0 18px;
      font-size: clamp(42px, 6.2vw, 86px);
      line-height: 0.89;
      letter-spacing: -0.075em;
    }

    .gradient-text {
      background: linear-gradient(100deg, #ffffff 0%, #b8f8ff 36%, #c7b8ff 65%, #ffd4e8 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }

    .lead {
      max-width: 760px;
      margin: 0;
      color: #bfcae6;
      font-size: 18px;
      line-height: 1.62;
    }

    .metric-row {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 28px;
      position: relative;
      z-index: 1;
    }

    .metric {
      min-height: 94px;
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px;
      background: rgba(255,255,255,0.055);
    }

    .metric b {
      display: block;
      font-size: 22px;
      letter-spacing: -0.03em;
      margin-bottom: 6px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .mission-card {
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      background: linear-gradient(160deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035));
      padding: 28px;
      min-height: 430px;
      display: grid;
      gap: 16px;
      align-content: start;
    }

    .section-label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 4px;
    }

    .section-label h2,
    .panel-title h2 {
      margin: 0;
      font-size: 22px;
      letter-spacing: -0.04em;
    }

    .section-label span,
    .panel-title span {
      color: var(--muted);
      font-size: 13px;
    }

    .status-matrix {
      display: grid;
      gap: 10px;
    }

    .status-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border: 1px solid var(--line);
      border-radius: 17px;
      background: rgba(3, 7, 18, 0.38);
      padding: 13px 14px;
    }

    .status-card span { color: var(--muted); font-size: 13px; }
    .status-card b { font-family: var(--mono); font-size: 13px; color: #eaf0ff; }

    .flow-steps {
      display: grid;
      gap: 10px;
      margin-top: 6px;
    }

    .flow-step {
      display: grid;
      grid-template-columns: 34px 1fr;
      gap: 12px;
      align-items: start;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .flow-step b {
      width: 28px;
      height: 28px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, rgba(71,232,255,0.24), rgba(165,107,255,0.18));
      color: #f8fbff;
      font-size: 12px;
      border: 1px solid rgba(255,255,255,0.16);
    }

    .workspace {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr) 350px;
      gap: 18px;
      padding: 0 26px 26px;
    }

    .glass {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: rgba(7, 12, 28, 0.66);
      box-shadow: 0 18px 58px rgba(0,0,0,0.26);
      backdrop-filter: blur(18px);
    }

    .control-panel,
    .conversation-panel,
    .evidence-panel { padding: 18px; }

    .panel-title {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
    }

    label {
      display: block;
      color: #dce6ff;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin: 14px 0 7px;
    }

    select,
    textarea {
      width: 100%;
      color: var(--text);
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.075);
      border-radius: 16px;
      padding: 12px 13px;
      outline: none;
    }

    select:focus,
    textarea:focus {
      border-color: rgba(71,232,255,0.68);
      box-shadow: 0 0 0 4px rgba(71,232,255,0.10);
    }

    textarea {
      min-height: 118px;
      resize: vertical;
      line-height: 1.5;
    }

    button {
      width: 100%;
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 17px;
      padding: 12px 14px;
      cursor: pointer;
      color: #041019;
      font-weight: 950;
      background: linear-gradient(135deg, var(--cyan), var(--blue));
      box-shadow: 0 18px 36px rgba(71,232,255,0.12);
      transition: transform 120ms ease, border-color 120ms ease, opacity 120ms ease, filter 120ms ease;
    }

    button:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.06); }
    button:disabled { opacity: 0.42; cursor: not-allowed; box-shadow: none; }

    button.secondary {
      background: rgba(255,255,255,0.075);
      color: #dfe8ff;
      box-shadow: none;
    }

    button.danger {
      background: rgba(255,92,122,0.14);
      color: #ffdbe2;
      box-shadow: none;
      border-color: rgba(255,92,122,0.26);
    }

    .session-card,
    .error-box,
    .boundary-note {
      border-radius: 17px;
      padding: 12px;
      margin-top: 12px;
      line-height: 1.48;
      font-size: 13px;
    }

    .session-card {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.055);
      color: var(--muted);
      word-break: break-word;
    }

    .session-card strong { color: #fff; }

    .error-box {
      border: 1px solid rgba(255,92,122,0.38);
      background: rgba(255,92,122,0.12);
      color: #ffd2dc;
    }

    .scenario-list {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }

    .scenario {
      position: relative;
      overflow: hidden;
      text-align: left;
      min-height: 84px;
      color: var(--text);
      background: linear-gradient(135deg, rgba(255,255,255,0.095), rgba(255,255,255,0.035));
      box-shadow: none;
    }

    .scenario::before {
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 5px;
      background: var(--blue);
    }

    .scenario.answer::before { background: var(--green); }
    .scenario.clarify::before { background: var(--amber); }
    .scenario.escalate::before { background: var(--red); }
    .scenario.handoff::before { background: var(--violet); }

    .scenario small {
      display: block;
      color: var(--muted);
      font-weight: 650;
      margin-top: 5px;
      line-height: 1.32;
    }

    .conversation-panel {
      min-height: 690px;
      display: flex;
      flex-direction: column;
    }

    .message-row {
      display: grid;
      grid-template-columns: 1fr 180px;
      gap: 10px;
      margin-bottom: 14px;
    }

    .conversation {
      display: grid;
      gap: 14px;
      overflow: auto;
      padding-right: 3px;
    }

    .empty-state {
      display: grid;
      place-items: center;
      min-height: 430px;
      border: 1px dashed rgba(255,255,255,0.18);
      border-radius: 24px;
      color: var(--muted);
      text-align: center;
      padding: 36px;
      background: radial-gradient(circle at 50% 0%, rgba(71,232,255,0.08), transparent 26rem);
    }

    .empty-state b {
      display: block;
      margin-bottom: 10px;
      color: var(--text);
      font-size: 24px;
      letter-spacing: -0.04em;
    }

    .turn {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(145deg, rgba(255,255,255,0.095), rgba(255,255,255,0.035));
      overflow: hidden;
    }

    .turn.answer { border-color: rgba(53,228,166,0.36); }
    .turn.clarify { border-color: rgba(255,200,87,0.40); }
    .turn.escalate { border-color: rgba(255,92,122,0.42); }
    .turn.handoff { border-color: rgba(165,107,255,0.44); }

    .turn-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 13px 15px;
      border-bottom: 1px solid rgba(255,255,255,0.10);
      background: rgba(0,0,0,0.16);
    }

    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      align-items: center;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 9px;
      border: 1px solid var(--line);
      color: #dfe8ff;
      background: rgba(255,255,255,0.06);
      font-size: 11px;
      font-weight: 950;
      letter-spacing: 0.045em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .badge.answer { color: #c8ffea; border-color: rgba(53,228,166,0.42); background: rgba(53,228,166,0.12); }
    .badge.clarify { color: #fff0c5; border-color: rgba(255,200,87,0.46); background: rgba(255,200,87,0.12); }
    .badge.escalate { color: #ffd4dc; border-color: rgba(255,92,122,0.48); background: rgba(255,92,122,0.12); }
    .badge.handoff { color: #eadbff; border-color: rgba(165,107,255,0.48); background: rgba(165,107,255,0.13); }
    .badge.abstain { color: #dce5f5; border-color: rgba(154,166,189,0.45); background: rgba(154,166,189,0.12); }

    .turn-body {
      display: grid;
      gap: 13px;
      padding: 16px;
    }

    .bubble {
      border-radius: 18px;
      padding: 13px 14px;
      line-height: 1.55;
    }

    .bubble.user {
      color: #ced8f0;
      background: rgba(255,255,255,0.055);
      border: 1px solid rgba(255,255,255,0.09);
    }

    .bubble.answer-text {
      color: #ffffff;
      background: rgba(71,232,255,0.075);
      border: 1px solid rgba(71,232,255,0.20);
      font-size: 17px;
      font-weight: 760;
    }

    .route-note {
      border-left: 3px solid var(--cyan);
      background: rgba(255,255,255,0.052);
      color: #bec9e2;
      padding: 11px 12px;
      border-radius: 14px;
      line-height: 1.46;
      font-size: 13px;
    }

    .record-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }

    .record {
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 17px;
      padding: 12px;
      background: rgba(2, 6, 18, 0.34);
    }

    .record strong {
      display: block;
      margin-bottom: 8px;
      color: #f7fbff;
      font-family: var(--mono);
      font-size: 12px;
    }

    .record dl {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 5px 10px;
      margin: 0;
      font-size: 12px;
    }

    .record dt { color: var(--faint); }
    .record dd { margin: 0; text-align: right; color: #dce7ff; }

    .evidence-panel {
      min-height: 690px;
      display: grid;
      align-content: start;
      gap: 14px;
    }

    .decision-orb {
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 30px;
      padding: 22px;
      min-height: 220px;
      background:
        radial-gradient(circle at 50% 0%, rgba(71,232,255,0.18), transparent 16rem),
        rgba(255,255,255,0.052);
      display: grid;
      align-content: center;
      justify-items: center;
      text-align: center;
    }

    .orb-route {
      width: 112px;
      height: 112px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      border: 1px solid rgba(255,255,255,0.18);
      background: conic-gradient(from 180deg, rgba(71,232,255,0.74), rgba(165,107,255,0.8), rgba(255,94,168,0.7), rgba(71,232,255,0.74));
      box-shadow: 0 0 50px rgba(71,232,255,0.18);
      color: #041019;
      font-weight: 950;
      font-size: 15px;
      margin-bottom: 16px;
    }

    .orb-route.answer { background: radial-gradient(circle, #aaffde, var(--green)); }
    .orb-route.clarify { background: radial-gradient(circle, #fff0bd, var(--amber)); }
    .orb-route.escalate { background: radial-gradient(circle, #ffd1db, var(--red)); }
    .orb-route.handoff { background: radial-gradient(circle, #ead7ff, var(--violet)); }
    .orb-route.abstain { background: radial-gradient(circle, #e6ebf6, var(--slate)); }

    .decision-orb p { margin: 0; color: var(--muted); line-height: 1.45; }

    .evidence-list {
      display: grid;
      gap: 9px;
    }

    .evidence-item {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 11px 12px;
      background: rgba(255,255,255,0.052);
    }

    .evidence-item span {
      display: block;
      color: var(--faint);
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 900;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }

    .evidence-item b {
      color: #edf4ff;
      font-size: 13px;
      word-break: break-word;
    }

    .boundary-note {
      border: 1px solid rgba(255,200,87,0.26);
      background: rgba(255,200,87,0.08);
      color: #ffe9b6;
    }

    .footer-band {
      margin: 0 26px 26px;
      border: 1px solid rgba(255,255,255,0.11);
      border-radius: 22px;
      padding: 13px 16px;
      color: var(--muted);
      background: rgba(0,0,0,0.22);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 13px;
    }

    @media (max-width: 1240px) {
      .workspace { grid-template-columns: 320px 1fr; }
      .evidence-panel { grid-column: 1 / -1; min-height: 0; }
    }

    @media (max-width: 940px) {
      .app { width: min(100vw - 24px, 1500px); padding-top: 12px; }
      .topbar, .hero, .workspace { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .hero { padding: 16px; }
      .workspace { padding: 0 16px 16px; }
      .metric-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .message-row { grid-template-columns: 1fr; }
      .hero-copy, .mission-card { min-height: 0; }
      .footer-band { margin: 0 16px 16px; }
    }
  </style>
</head>
<body>
  <main class="app">
    <div class="chrome">
      <header class="topbar">
        <div class="brand">
          <div class="mark" aria-hidden="true">1</div>
          <div class="brand-title">
            <strong>Proof of One</strong>
            <span>Judge-facing visual prototype over the local synthetic API</span>
          </div>
        </div>
        <div class="limit-strip" aria-label="demo boundaries">
          <span class="chip cyan">Synthetic demo</span>
          <span class="chip">Deterministic routes</span>
          <span class="chip warn">No live provider</span>
          <span class="chip pink">Not production</span>
        </div>
      </header>

      <section class="hero">
        <div class="hero-copy">
          <div class="kicker"><span class="pulse-dot"></span> Local API connected demo shell</div>
          <h1><span class="gradient-text">Bilingual payment support</span><br>over verified records.</h1>
          <p class="lead">
            A cinematic local demo for a bounded customer-support system: the UI sends messages to the existing FastAPI backend, then surfaces the deterministic route, verified facts, and handoff evidence returned by the API.
          </p>
          <div class="metric-row">
            <div class="metric"><b>ES / PT</b><span>Spanish and Portuguese synthetic support paths.</span></div>
            <div class="metric"><b>4 routes</b><span>ANSWER, CLARIFY, ESCALATE, and ABSTAIN boundaries.</span></div>
            <div class="metric"><b>0 live LLM</b><span>No provider is connected in this local demo.</span></div>
            <div class="metric"><b>1 identity</b><span>Customer identity is established by the server session.</span></div>
          </div>
        </div>

        <aside class="mission-card">
          <div class="section-label">
            <div>
              <h2>Runtime status</h2>
              <span>Read directly from the local readiness endpoint.</span>
            </div>
            <span class="chip cyan">/ready</span>
          </div>
          <div class="status-matrix">
            <div class="status-card"><span>Readiness</span><b id="ready-status">checking…</b></div>
            <div class="status-card"><span>Data mode</span><b id="data-mode">checking…</b></div>
            <div class="status-card"><span>LLM connected</span><b id="llm-connected">checking…</b></div>
          </div>
          <div class="flow-steps" aria-label="demo control flow">
            <div class="flow-step"><b>1</b><span>The server issues a session for Lucía or Rafael. The browser never supplies a customer ID.</span></div>
            <div class="flow-step"><b>2</b><span>The message is resolved against that persona's synthetic records by the existing backend.</span></div>
            <div class="flow-step"><b>3</b><span>The UI displays the returned route, reason codes, records, and ticket evidence without changing policy logic.</span></div>
          </div>
          <div class="boundary-note">
            Claim boundary: this is a judge-facing visual prototype over the existing local synthetic API. It is not a production, pilot, live-provider, or IPA-M1-closure claim.
          </div>
        </aside>
      </section>

      <section class="workspace">
        <aside class="glass control-panel">
          <div class="panel-title">
            <div>
              <h2>Scenario launcher</h2>
              <span>One-click paths for the judge demo.</span>
            </div>
          </div>

          <label for="persona">Persona</label>
          <select id="persona"></select>

          <label for="language">Language</label>
          <select id="language">
            <option value="">Use persona default</option>
            <option value="es">Spanish</option>
            <option value="pt">Portuguese</option>
          </select>

          <button id="start-session">Start / reset session</button>
          <button id="handoff" class="secondary" disabled>Request support handoff</button>
          <button id="revoke" class="danger" disabled>Revoke session</button>

          <div class="session-card" id="session-box">No active session.</div>
          <div id="error-box" class="error-box" hidden></div>

          <div class="scenario-list" aria-label="demo scenarios">
            <button class="scenario answer" data-persona="lucia" data-message="¿Cuál es el estado de la transacción DEMO-ES-1001?">
              ANSWER · Known transaction
              <small>Returns verified status and amount for Lucía's synthetic payment.</small>
            </button>
            <button class="scenario clarify" data-persona="lucia" data-message="Quiero consultar una transacción por 54000 COP.">
              CLARIFY · Two possible matches
              <small>Two verified payments match the amount, so the system asks which one.</small>
            </button>
            <button class="scenario escalate" data-persona="lucia" data-message="No reconozco la transacción DEMO-ES-1001. Yo no autoricé ese pago.">
              ESCALATE · Unauthorized report
              <small>Customer-reported unauthorized activity creates a support ticket. This is not fraud detection.</small>
            </button>
            <button class="scenario handoff" data-persona="lucia" data-action="handoff">
              HANDOFF · Human support request
              <small>Creates a persisted and verified demo support ticket.</small>
            </button>
            <button class="scenario answer" data-persona="rafael" data-message="Quero consultar a transação DEMO-PT-2003.">
              PT · Portuguese support path
              <small>Rafael's flow shows the same route boundary in Portuguese.</small>
            </button>
          </div>
        </aside>

        <section class="glass conversation-panel">
          <div class="panel-title">
            <div>
              <h2>Customer support workbench</h2>
              <span>The center panel is what the judge should watch.</span>
            </div>
            <span class="chip">local API</span>
          </div>
          <label for="message">Customer message</label>
          <div class="message-row">
            <textarea id="message" placeholder="Choose a scenario or type a supported customer message…"></textarea>
            <button id="send" disabled>Send message</button>
          </div>
          <div class="conversation" id="conversation">
            <div class="empty-state"><div><b>Ready for a route.</b>Select a scenario on the left to start the session and send a demo message.</div></div>
          </div>
        </section>

        <aside class="glass evidence-panel">
          <div class="panel-title">
            <div>
              <h2>Decision intelligence</h2>
              <span>Current route and supporting evidence.</span>
            </div>
          </div>
          <div class="decision-orb">
            <div class="orb-route" id="current-route">READY</div>
            <p id="current-explanation">Run a scenario to display route, intent, reason codes, synthetic mode, and ticket evidence.</p>
          </div>
          <div class="evidence-list" id="evidence-list">
            <div class="evidence-item"><span>Scope</span><b>Synthetic local demo only</b></div>
            <div class="evidence-item"><span>Authority</span><b>Backend route, not UI discretion</b></div>
            <div class="evidence-item"><span>Provider</span><b>No live LLM connected</b></div>
          </div>
        </aside>
      </section>

      <footer class="footer-band">
        <span>Visual prototype shell over the existing local API; API screenshots remain technical evidence.</span>
        <span>Synthetic data only · no live provider · not production · final submission requires separate owner approval.</span>
      </footer>
    </div>
  </main>

  <script>
    const state = { personas: [], session: null, turns: [], lastEvidence: null };

    const els = {
      readyStatus: document.getElementById('ready-status'),
      dataMode: document.getElementById('data-mode'),
      llmConnected: document.getElementById('llm-connected'),
      persona: document.getElementById('persona'),
      language: document.getElementById('language'),
      start: document.getElementById('start-session'),
      handoff: document.getElementById('handoff'),
      revoke: document.getElementById('revoke'),
      sessionBox: document.getElementById('session-box'),
      error: document.getElementById('error-box'),
      message: document.getElementById('message'),
      send: document.getElementById('send'),
      conversation: document.getElementById('conversation'),
      currentRoute: document.getElementById('current-route'),
      currentExplanation: document.getElementById('current-explanation'),
      evidenceList: document.getElementById('evidence-list')
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

    function routeKey(route) {
      return String(route || '').toLowerCase();
    }

    function routeExplanation(route, reasonCodes = []) {
      const has = (code) => reasonCodes.includes(code);
      if (route === 'ANSWER') return 'Verified synthetic records matched the supported request. The UI is showing facts returned by the backend.';
      if (route === 'CLARIFY' && has('ambiguous_transaction_match')) return 'More than one verified record matched. The backend asks the customer to choose instead of guessing.';
      if (route === 'CLARIFY') return 'The backend needs more detail before it can safely identify one verified record.';
      if (route === 'ESCALATE' && has('unauthorized_activity_reported')) return 'The customer reported unauthorized activity. The demo creates a support ticket; this is not fraud detection.';
      if (route === 'ESCALATE') return 'A conservative rule opened a support path rather than answering automatically.';
      if (route === 'ABSTAIN') return 'The request is outside the supported surface, so the system does not invent an answer.';
      if (route === 'HANDOFF') return 'The customer explicitly requested support, so the API returned persisted ticket evidence.';
      return 'Run a scenario to see the deterministic route returned by the local API.';
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
          style: 'currency', currency: currency || 'USD', currencyDisplay: 'code'
        }).format(numeric).replace(/\u00a0/g, ' ');
      } catch (error) {
        return `${numeric.toLocaleString()} ${currency || ''}`.trim();
      }
    }

    function formatTimestamp(value) {
      if (!value) return '—';
      return String(value).replace('T', ' ').slice(0, 16);
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

    function renderEvidence(turn) {
      const response = turn?.response || {};
      const route = response.route || turn?.kind || 'READY';
      const routeClass = routeKey(route);
      els.currentRoute.className = `orb-route ${routeClass}`;
      els.currentRoute.textContent = route;
      els.currentExplanation.textContent = routeExplanation(route, response.reason_codes || []);

      const evidence = [];
      if (response.intent && response.intent !== 'unknown') evidence.push(['Intent', response.intent]);
      if (response.reason_codes?.length) evidence.push(['Reason codes', response.reason_codes.join(', ')]);
      if (response.synthetic_data !== undefined) evidence.push(['Synthetic data', String(response.synthetic_data)]);
      if (response.escalation_ticket_id) evidence.push(['Ticket ID', response.escalation_ticket_id]);
      if (response.persisted !== undefined) evidence.push(['Persisted', String(response.persisted)]);
      if (response.verified !== undefined) evidence.push(['Verified', String(response.verified)]);
      if (response.clarification_transaction_ids?.length) evidence.push(['Clarification candidates', response.clarification_transaction_ids.join(', ')]);
      if (!evidence.length) {
        evidence.push(['Scope', 'Synthetic local demo only']);
        evidence.push(['Authority', 'Backend route, not UI discretion']);
        evidence.push(['Provider', 'No live LLM connected']);
      }

      els.evidenceList.innerHTML = evidence.map(([label, value]) => `
        <div class="evidence-item"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>
      `).join('');
    }

    function renderConversation() {
      if (!state.turns.length) {
        els.conversation.innerHTML = '<div class="empty-state"><div><b>Ready for a route.</b>Select a scenario on the left to start the session and send a demo message.</div></div>';
        renderEvidence(null);
        return;
      }
      els.conversation.innerHTML = state.turns.map((turn) => {
        const response = turn.response || {};
        const route = response.route || turn.kind || 'EVENT';
        const cls = routeKey(route);
        const records = [...(response.products || []), ...(response.transactions || [])];
        const candidates = response.clarification_transaction_ids || [];
        const intent = response.intent && response.intent !== 'unknown' ? response.intent : '';
        return `
          <article class="turn ${cls}">
            <header class="turn-head">
              <div class="badge-row">
                <span class="badge ${cls}">${escapeHtml(route)}</span>
                ${intent ? `<span class="badge">${escapeHtml(intent)}</span>` : ''}
                ${response.synthetic_data ? '<span class="badge">synthetic data</span>' : ''}
              </div>
              ${response.escalation_ticket_id ? `<span class="badge ${cls}">ticket ${escapeHtml(response.escalation_ticket_id)}</span>` : ''}
            </header>
            <div class="turn-body">
              ${turn.message ? `<div class="bubble user"><strong>Customer</strong><br>${escapeHtml(turn.message)}</div>` : ''}
              <div class="bubble answer-text">${escapeHtml(response.response_text || turn.text || '')}</div>
              <div class="route-note">${escapeHtml(routeExplanation(route, response.reason_codes || []))}</div>
              ${response.reason_codes?.length ? `<div class="badge-row">${response.reason_codes.map((reason) => `<span class="badge">${escapeHtml(reason)}</span>`).join('')}</div>` : ''}
              ${candidates.length ? `<div class="record"><strong>Clarification candidates</strong><div>${candidates.map(escapeHtml).join(', ')}</div></div>` : ''}
              ${records.length ? `<div class="record-grid">${records.map(renderRecord).join('')}</div>` : ''}
            </div>
          </article>`;
      }).join('');
      renderEvidence(state.turns[0]);
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
        <strong>${escapeHtml(state.session.display_name)}</strong><br>
        Session: ${escapeHtml(state.session.session_id)}<br>
        Role: ${escapeHtml(state.session.role)} · Language: ${escapeHtml(state.session.language)}<br>
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
        els.llmConnected.textContent = String(ready.llm_connected);
      } catch (error) {
        els.readyStatus.textContent = 'not_ready';
        els.dataMode.textContent = 'unknown';
        els.llmConnected.textContent = 'false';
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
        method: 'POST', headers: {}, body: JSON.stringify(body)
      });
      state.turns = [];
      renderSession();
      renderConversation();
    }

    async function ensureScenarioSession(personaId) {
      if (personaId) els.persona.value = personaId;
      if (!state.session || state.session.persona_id !== els.persona.value) {
        await startSession();
      }
    }

    async function sendTurn() {
      setError('');
      const message = els.message.value.trim();
      if (!message) return;
      if (!state.session) await startSession();
      if (state.session && els.persona.value !== state.session.persona_id) {
        setError('The selected persona differs from the active session. Start/reset the session before sending.');
        return;
      }
      const response = await api('/api/customer/turn', {
        method: 'POST', body: JSON.stringify({message})
      });
      state.turns.unshift({message, response});
      renderConversation();
    }

    async function requestHandoff() {
      setError('');
      if (!state.session) await startSession();
      const response = await api('/api/customer/handoff', {method: 'POST', body: '{}'});
      const handoffText = response.persisted && response.verified
        ? `Support ticket created and verified. Ticket: ${response.ticket_id}`
        : `Handoff response received. Ticket: ${response.ticket_id || 'not returned'}`;
      state.turns.unshift({
        kind: 'HANDOFF',
        text: handoffText,
        response: {
          route: 'HANDOFF',
          intent: 'customer_requested_support_handoff',
          response_text: handoffText,
          escalation_ticket_id: response.ticket_id,
          persisted: response.persisted,
          verified: response.verified,
          synthetic_data: state.session?.synthetic_data === true
        }
      });
      renderConversation();
    }

    async function revokeSession() {
      setError('');
      await api('/api/demo/session', {method: 'DELETE', body: '{}'});
      state.session = null;
      state.turns = [];
      renderSession();
      renderConversation();
    }

    els.start.addEventListener('click', () => startSession().catch((error) => setError(error.message)));
    els.send.addEventListener('click', () => sendTurn().catch((error) => setError(error.message)));
    els.handoff.addEventListener('click', () => requestHandoff().catch((error) => setError(error.message)));
    els.revoke.addEventListener('click', () => revokeSession().catch((error) => setError(error.message)));

    document.querySelectorAll('.scenario').forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          setError('');
          await ensureScenarioSession(button.dataset.persona || 'lucia');
          if (button.dataset.action === 'handoff') {
            await requestHandoff();
            return;
          }
          els.message.value = button.dataset.message || '';
          await sendTurn();
        } catch (error) {
          setError(error.message);
        }
      });
    });

    Promise.all([loadReady(), loadPersonas()]).catch((error) => setError(error.message));
    renderSession();
    renderConversation();
  </script>
</body>
</html>
"""


def render_demo_ui() -> str:
    """Return the dependency-free judge-facing local demo shell."""

    return DEMO_UI_HTML
