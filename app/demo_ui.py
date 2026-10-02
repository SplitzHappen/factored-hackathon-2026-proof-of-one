from __future__ import annotations


DEMO_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof of One — Judge Demo Shell</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d8dde8;
      --accent: #3457d5;
      --accent-dark: #233b91;
      --good: #166534;
      --warn: #92400e;
      --danger: #991b1b;
      --chip: #eef2ff;
      --shadow: 0 18px 45px rgba(23, 32, 51, 0.10);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: radial-gradient(circle at top left, #eef2ff 0, #f6f7fb 36rem);
      color: var(--ink);
    }

    .shell {
      max-width: 1240px;
      margin: 0 auto;
      padding: 28px;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.65fr);
      gap: 22px;
      align-items: stretch;
      margin-bottom: 22px;
    }

    .panel {
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }

    .hero-copy { padding: 30px; }

    .eyebrow {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--chip);
      color: var(--accent-dark);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    h1 {
      margin: 18px 0 12px;
      font-size: clamp(34px, 6vw, 58px);
      line-height: 0.95;
      letter-spacing: -0.055em;
    }

    .lead {
      max-width: 780px;
      margin: 0;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.55;
    }

    .claim-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 24px;
    }

    .claim {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #fbfcff;
    }

    .claim strong {
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
    }

    .claim span {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .status-card {
      padding: 24px;
      display: grid;
      gap: 16px;
      align-content: start;
    }

    .status-line {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
    }

    .status-line:last-child { border-bottom: 0; }
    .status-line span:first-child { color: var(--muted); }
    .status-line span:last-child { font-weight: 700; text-align: right; }

    .main-grid {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .sidebar, .workbench { padding: 22px; }
    h2 { margin: 0 0 14px; font-size: 22px; letter-spacing: -0.02em; }
    h3 { margin: 0 0 10px; font-size: 16px; }

    label {
      display: block;
      margin: 14px 0 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    select, textarea, button {
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      font: inherit;
    }

    select, textarea {
      background: #fff;
      color: var(--ink);
      padding: 12px 14px;
    }

    textarea {
      min-height: 110px;
      resize: vertical;
      line-height: 1.45;
    }

    button {
      margin-top: 12px;
      padding: 12px 14px;
      background: var(--accent);
      color: white;
      border-color: var(--accent);
      font-weight: 800;
      cursor: pointer;
      transition: transform 120ms ease, background 120ms ease;
    }

    button:hover { background: var(--accent-dark); transform: translateY(-1px); }
    button.secondary { background: #fff; color: var(--accent-dark); border-color: #b9c3ff; }
    button.secondary:hover { background: #f5f7ff; }
    button.danger { background: #fff; color: var(--danger); border-color: #fecaca; }
    button.danger:hover { background: #fff5f5; }
    button:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }

    .scenario-list {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }

    .scenario {
      text-align: left;
      background: #fff;
      color: var(--ink);
      border-color: var(--line);
      font-weight: 700;
      margin: 0;
    }

    .scenario small {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-weight: 500;
      line-height: 1.35;
    }

    .conversation {
      display: grid;
      gap: 14px;
      min-height: 360px;
    }

    .empty {
      padding: 32px;
      border: 1px dashed var(--line);
      border-radius: 18px;
      color: var(--muted);
      text-align: center;
      background: #fbfcff;
    }

    .turn {
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #fff;
    }

    .turn-header {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
      padding: 12px 14px;
      background: #f8faff;
      border-bottom: 1px solid var(--line);
    }

    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 800;
      background: #eef2ff;
      color: var(--accent-dark);
    }

    .pill.answer { background: #dcfce7; color: var(--good); }
    .pill.clarify { background: #fef3c7; color: var(--warn); }
    .pill.escalate { background: #fee2e2; color: var(--danger); }
    .pill.abstain { background: #e5e7eb; color: #374151; }

    .turn-body { padding: 14px; display: grid; gap: 14px; }
    .user-text { color: var(--muted); font-size: 14px; }
    .answer-text { font-size: 16px; line-height: 1.55; }

    .data-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }

    .record {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: #fbfcff;
      font-size: 13px;
    }

    .record strong { display: block; margin-bottom: 5px; }
    .record dl { margin: 0; display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 4px 8px; }
    .record dt { color: var(--muted); }
    .record dd { margin: 0; overflow-wrap: anywhere; }

    .callout {
      margin-top: 16px;
      padding: 14px;
      border: 1px solid #bfdbfe;
      border-radius: 16px;
      background: #eff6ff;
      color: #1e3a8a;
      font-size: 13px;
      line-height: 1.45;
    }

    .session-box {
      margin-top: 14px;
      padding: 12px;
      border-radius: 14px;
      background: #fbfcff;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }

    .error {
      margin-top: 12px;
      padding: 12px;
      border-radius: 14px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: var(--danger);
      font-size: 13px;
      line-height: 1.4;
    }

    @media (max-width: 920px) {
      .hero, .main-grid { grid-template-columns: 1fr; }
      .claim-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 560px) {
      .shell { padding: 16px; }
      .hero-copy, .status-card, .sidebar, .workbench { padding: 18px; }
      .claim-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="panel hero-copy">
        <div class="eyebrow">Proof of One · local judge shell</div>
        <h1>Bounded support decisions over verified banking facts.</h1>
        <p class="lead">
          This shell is a screenshot-ready interface over the existing local FastAPI demo API.
          It shows the allowed demo flows without adding model authority, live-provider wiring,
          production claims, or hidden customer identity controls.
        </p>
        <div class="claim-grid" aria-label="claim limits">
          <div class="claim"><strong>Server-issued session</strong><span>The browser receives a demo session; it never submits customer_id.</span></div>
          <div class="claim"><strong>Synthetic facts only</strong><span>Displayed personas and records come from the public synthetic artifact.</span></div>
          <div class="claim"><strong>Deterministic routing</strong><span>ANSWER, CLARIFY, ABSTAIN, and ESCALATE remain backend decisions.</span></div>
          <div class="claim"><strong>Human handoff path</strong><span>Escalations show persisted ticket evidence where the API provides it.</span></div>
        </div>
      </div>
      <aside class="panel status-card" aria-label="runtime status">
        <h2>Runtime boundary</h2>
        <div class="status-line"><span>API readiness</span><span id="ready-status">checking…</span></div>
        <div class="status-line"><span>Data mode</span><span id="data-mode">unknown</span></div>
        <div class="status-line"><span>LLM connected</span><span id="llm-connected">false</span></div>
        <div class="status-line"><span>Scope</span><span>local synthetic demo</span></div>
        <div class="callout">
          Claim limit: this interface demonstrates the existing local API flow. It does not claim production readiness, live-provider readiness, or final judge submission approval.
        </div>
      </aside>
    </section>

    <section class="main-grid">
      <aside class="panel sidebar">
        <h2>Demo controls</h2>
        <label for="persona">Persona</label>
        <select id="persona"></select>

        <label for="language">Language</label>
        <select id="language">
          <option value="">Use persona default</option>
          <option value="es">Spanish</option>
          <option value="pt">Portuguese</option>
        </select>

        <button id="start-session">Start new demo session</button>
        <button id="handoff" class="secondary" disabled>Request support handoff</button>
        <button id="revoke" class="danger" disabled>Revoke session</button>
        <div class="session-box" id="session-box">No active session.</div>
        <div id="error-box" class="error" hidden></div>

        <div class="scenario-list" aria-label="preset scenarios">
          <h3>Preset judge flows</h3>
          <button class="scenario" data-message="Muéstrame mis últimos movimientos.">
            ANSWER · Recent movements
            <small>Supported request over verified synthetic transaction facts.</small>
          </button>
          <button class="scenario" data-message="¿Cuál fue el pago de 54.000 COP?">
            CLARIFY · Ambiguous payment
            <small>Two matching demo transactions require a customer clarification.</small>
          </button>
          <button class="scenario" data-message="No reconozco este pago y no autoricé esta actividad en mi cuenta.">
            ESCALATE · Unauthorized activity
            <small>Safety precedence routes reported unauthorized activity to human review.</small>
          </button>
          <button class="scenario" data-message="Quero ver meus pagamentos recentes.">
            PT · Portuguese support
            <small>Uses the same bounded API path for the Portuguese demo persona.</small>
          </button>
        </div>
      </aside>

      <section class="panel workbench">
        <h2>Customer support workbench</h2>
        <label for="message">Customer message</label>
        <textarea id="message" placeholder="Start a session, then send a customer message…"></textarea>
        <button id="send" disabled>Send to local API</button>
        <div class="conversation" id="conversation">
          <div class="empty">Start a session and run one of the preset judge flows.</div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const state = {
      personas: [],
      session: null,
      turns: []
    };

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
      conversation: document.getElementById('conversation')
    };

    function setError(message) {
      if (!message) {
        els.error.hidden = true;
        els.error.textContent = '';
        return;
      }
      els.error.hidden = false;
      els.error.textContent = message;
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
      if (response.status === 204) {
        return null;
      }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
        throw new Error(detail || `HTTP ${response.status}`);
      }
      return body;
    }

    function routeClass(route) {
      if (route === 'ANSWER') return 'answer';
      if (route === 'CLARIFY') return 'clarify';
      if (route === 'ESCALATE') return 'escalate';
      if (route === 'ABSTAIN') return 'abstain';
      return '';
    }

    function formatMoney(value, currency) {
      if (value === undefined || value === null) return '—';
      const numeric = Number(value);
      if (Number.isNaN(numeric)) return `${value} ${currency || ''}`.trim();
      return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(numeric);
    }

    function renderRecord(record) {
      return `
        <div class="record">
          <strong>${record.transaction_id || record.product_id || 'Record'}</strong>
          <dl>
            ${record.occurred_at ? `<dt>Date</dt><dd>${record.occurred_at}</dd>` : ''}
            ${record.transaction_type ? `<dt>Type</dt><dd>${record.transaction_type}</dd>` : ''}
            ${record.status ? `<dt>Status</dt><dd>${record.status}</dd>` : ''}
            ${record.amount !== undefined ? `<dt>Amount</dt><dd>${formatMoney(record.amount, record.currency)}</dd>` : ''}
            ${record.merchant_name ? `<dt>Merchant</dt><dd>${record.merchant_name}</dd>` : ''}
            ${record.product_type ? `<dt>Product</dt><dd>${record.product_type}</dd>` : ''}
            ${record.current_balance !== undefined ? `<dt>Balance</dt><dd>${formatMoney(record.current_balance, record.currency)}</dd>` : ''}
          </dl>
        </div>`;
    }

    function renderConversation() {
      if (!state.turns.length) {
        els.conversation.innerHTML = '<div class="empty">Start a session and run one of the preset judge flows.</div>';
        return;
      }
      els.conversation.innerHTML = state.turns.map((turn) => {
        const response = turn.response || {};
        const route = response.route || turn.kind || 'EVENT';
        const records = [
          ...(response.products || []),
          ...(response.transactions || [])
        ];
        const candidates = response.clarification_transaction_ids || [];
        return `
          <article class="turn">
            <header class="turn-header">
              <div class="pill-row">
                <span class="pill ${routeClass(route)}">${route}</span>
                ${response.intent ? `<span class="pill">${response.intent}</span>` : ''}
                ${response.synthetic_data ? '<span class="pill">synthetic data</span>' : ''}
              </div>
              ${response.escalation_ticket_id ? `<span class="pill escalate">ticket ${response.escalation_ticket_id}</span>` : ''}
            </header>
            <div class="turn-body">
              ${turn.message ? `<div class="user-text"><strong>Customer:</strong> ${turn.message}</div>` : ''}
              <div class="answer-text">${response.response_text || turn.text || ''}</div>
              ${response.reason_codes?.length ? `<div class="pill-row">${response.reason_codes.map((reason) => `<span class="pill">${reason}</span>`).join('')}</div>` : ''}
              ${candidates.length ? `<div class="record"><strong>Clarification candidates</strong><div>${candidates.join(', ')}</div></div>` : ''}
              ${records.length ? `<div class="data-grid">${records.map(renderRecord).join('')}</div>` : ''}
            </div>
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
        <strong>${state.session.display_name}</strong><br>
        Session: ${state.session.session_id}<br>
        Tenant: ${state.session.tenant_id}<br>
        Role: ${state.session.role}<br>
        Language: ${state.session.language}<br>
        Synthetic data: ${state.session.synthetic_data}`;
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
      }
    }

    async function loadPersonas() {
      state.personas = await api('/api/demo/personas', {headers: {}});
      els.persona.innerHTML = state.personas.map((persona) => (
        `<option value="${persona.persona_id}">${persona.display_name} · ${persona.default_language.toUpperCase()}</option>`
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
      renderSession();
      renderConversation();
    }

    async function sendTurn() {
      setError('');
      const message = els.message.value.trim();
      if (!message) return;
      const response = await api('/api/customer/turn', {
        method: 'POST',
        body: JSON.stringify({message})
      });
      state.turns.unshift({message, response});
      renderConversation();
    }

    async function requestHandoff() {
      setError('');
      const response = await api('/api/customer/handoff', {method: 'POST', body: '{}'});
      state.turns.unshift({
        kind: 'ESCALATE',
        text: `Support handoff persisted and verified. Ticket: ${response.ticket_id}`,
        response: {
          route: 'ESCALATE',
          intent: 'customer_requested_support_handoff',
          response_text: `Support handoff persisted and verified. Ticket: ${response.ticket_id}`,
          reason_codes: ['customer_requested_support_handoff'],
          escalation_ticket_id: response.ticket_id,
          synthetic_data: true
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
      button.addEventListener('click', () => {
        els.message.value = button.dataset.message || '';
      });
    });

    Promise.all([loadReady(), loadPersonas()]).catch((error) => setError(error.message));
    renderSession();
  </script>
</body>
</html>
"""


def render_demo_ui() -> str:
    """Return the dependency-free judge-facing local demo shell."""

    return DEMO_UI_HTML
