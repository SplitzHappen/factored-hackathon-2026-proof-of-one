from __future__ import annotations


DEMO_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof of One — Local Synthetic Demo</title>
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
      max-width: 760px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.55;
      margin: 0 0 22px;
    }

    .claim-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .claim {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #ffffff;
    }

    .claim strong,
    .runtime-card strong {
      display: block;
      margin-bottom: 5px;
      font-size: 15px;
    }

    .claim span,
    .runtime-card span {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    .runtime-card {
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 16px;
    }

    .runtime-card h2 {
      margin-bottom: 8px;
    }

    .status-grid {
      display: grid;
      gap: 12px;
    }

    .status-line {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 10px;
      color: var(--muted);
    }

    .status-line b { color: var(--ink); }

    .runtime-steps {
      display: grid;
      gap: 10px;
      margin: 2px 0 0;
      padding: 0;
      list-style: none;
    }

    .runtime-steps li {
      display: grid;
      grid-template-columns: 30px 1fr;
      gap: 10px;
      align-items: start;
    }

    .runtime-steps b {
      display: inline-flex;
      justify-content: center;
      align-items: center;
      width: 26px;
      height: 26px;
      border-radius: 999px;
      background: var(--chip);
      color: var(--accent-dark);
      font-size: 12px;
    }

    .runtime-steps span {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }

    .callout {
      border-left: 4px solid var(--accent);
      background: #f8fafc;
      padding: 14px 16px;
      border-radius: 14px;
      margin-top: 18px;
      color: var(--muted);
      line-height: 1.5;
    }

    .main-grid {
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .sidebar,
    .workbench { padding: 22px; }

    h2 {
      margin: 0 0 16px;
      letter-spacing: -0.025em;
    }

    h3 {
      margin: 20px 0 10px;
      font-size: 14px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    label {
      display: block;
      font-weight: 700;
      font-size: 13px;
      margin: 14px 0 6px;
    }

    select,
    textarea,
    button {
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      font: inherit;
    }

    select,
    textarea {
      background: #ffffff;
      color: var(--ink);
      padding: 12px;
    }

    textarea {
      min-height: 118px;
      resize: vertical;
      line-height: 1.5;
    }

    button {
      margin-top: 10px;
      border: 0;
      background: var(--accent);
      color: #ffffff;
      font-weight: 800;
      padding: 12px 14px;
      cursor: pointer;
    }

    button:hover:not(:disabled) { background: var(--accent-dark); }
    button:disabled { opacity: 0.45; cursor: not-allowed; }

    button.secondary {
      background: #eef2ff;
      color: var(--accent-dark);
      border: 1px solid #c7d2fe;
    }

    button.danger { background: #fee2e2; color: var(--danger); }

    .scenario {
      text-align: left;
      background: #ffffff;
      color: var(--ink);
      border: 1px solid var(--line);
      font-weight: 800;
    }

    .scenario small {
      display: block;
      color: var(--muted);
      font-weight: 500;
      margin-top: 4px;
      line-height: 1.35;
    }

    .session-box,
    .error {
      margin-top: 14px;
      border-radius: 14px;
      padding: 12px;
      line-height: 1.45;
      font-size: 13px;
    }

    .session-box {
      background: #f8fafc;
      border: 1px solid var(--line);
      color: var(--muted);
      word-break: break-word;
    }

    .error {
      color: var(--danger);
      background: #fef2f2;
      border: 1px solid #fecaca;
    }

    .conversation {
      display: grid;
      gap: 14px;
      margin-top: 18px;
    }

    .empty {
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 18px;
      padding: 32px;
      text-align: center;
    }

    .turn {
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      background: #ffffff;
    }

    .turn-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      background: #f8fafc;
      border-bottom: 1px solid var(--line);
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 9px;
      background: #eef2ff;
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.02em;
    }

    .pill.answer { background: #dcfce7; color: var(--good); }
    .pill.clarify { background: #fef3c7; color: var(--warn); }
    .pill.escalate { background: #fee2e2; color: var(--danger); }
    .pill.abstain { background: #f1f5f9; color: #334155; }
    .pill.handoff { background: #fee2e2; color: var(--danger); }

    .turn-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }

    .user-text,
    .answer-text {
      line-height: 1.55;
    }

    .user-text {
      color: var(--muted);
    }

    .answer-text {
      font-size: 17px;
      font-weight: 650;
    }

    .route-explanation {
      color: var(--muted);
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      line-height: 1.45;
      font-size: 14px;
    }

    .data-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
    }

    .record {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: #fcfcfd;
    }

    .record dl {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 10px;
      margin: 8px 0 0;
      font-size: 13px;
    }

    .record dt { color: var(--muted); }
    .record dd { margin: 0; text-align: right; }

    @media (max-width: 920px) {
      .hero,
      .main-grid,
      .claim-grid { grid-template-columns: 1fr; }
      .shell { padding: 18px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="panel hero-copy">
        <div class="eyebrow">Proof of One · local synthetic demo</div>
        <h1>Bounded support decisions over verified synthetic account records.</h1>
        <p class="lead">
          A local demo of the Proof of One support API, running on fictional customers and transactions.
          Every route below is decided by deterministic backend rules; no language model is connected in this demo.
        </p>
        <div class="claim-grid">
          <div class="claim">
            <strong>Server-controlled identity</strong>
            <span>The browser never chooses which customer it sees; the server assigns it.</span>
          </div>
          <div class="claim">
            <strong>Synthetic data only</strong>
            <span>All customers and transactions shown are fictional demo records.</span>
          </div>
          <div class="claim">
            <strong>Deterministic route boundary</strong>
            <span>ANSWER, CLARIFY, ABSTAIN, and ESCALATE are backend decisions, not UI labels.</span>
          </div>
          <div class="claim">
            <strong>Support ticket on escalation</strong>
            <span>Escalations create a stored support ticket for follow-up. No live agent is connected in this demo.</span>
          </div>
        </div>
        <div class="callout">
          <strong>Demo limits:</strong> synthetic data only · runs locally · no language model connected · not a production system.
        </div>
      </div>

      <aside class="panel runtime-card">
        <div>
          <h2>Runtime boundary</h2>
          <span>Live state from the local API readiness endpoint.</span>
        </div>
        <div class="status-grid">
          <div class="status-line"><span>Readiness</span><b id="ready-status">checking…</b></div>
          <div class="status-line"><span>Data mode</span><b id="data-mode">checking…</b></div>
          <div class="status-line"><span>LLM connected</span><b id="llm-connected">checking…</b></div>
        </div>
        <ul class="runtime-steps" aria-label="message handling steps">
          <li><b>1</b><span>The server issues a demo session for one fictional customer.</span></li>
          <li><b>2</b><span>The local API checks the message against verified synthetic records.</span></li>
          <li><b>3</b><span>The backend returns a bounded route: answer, clarify, abstain, or ticket.</span></li>
        </ul>
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

        <div class="scenario-list" aria-label="demo scenarios">
          <h3>Demo scenarios</h3>
          <button class="scenario" data-persona="lucia" data-message="Muéstrame mis últimos movimientos.">
            ANSWER · Recent movements
            <small>Supported request over verified synthetic transaction facts. (Lucía)</small>
          </button>
          <button class="scenario" data-persona="lucia" data-message="Busca las transacciones de 54.000 COP.">
            CLARIFY · Ambiguous payment
            <small>Two verified transactions match this amount, so the system asks which one the customer means. (Lucía)</small>
          </button>
          <button class="scenario" data-persona="lucia" data-message="Quiero la transacción DEMO-ES-1003.">
            ANSWER · Resolve clarification
            <small>After the CLARIFY result, this selects one candidate and returns the matching record. (Lucía)</small>
          </button>
          <button class="scenario" data-persona="lucia" data-message="No reconozco este pago y no autoricé esta actividad en mi cuenta.">
            ESCALATE · Unauthorized activity
            <small>When the customer reports activity they did not authorize, a deterministic rule opens a support ticket. This is not fraud detection.</small>
          </button>
          <button class="scenario" data-persona="rafael" data-message="Quero ver meus pagamentos recentes.">
            PT · Portuguese support (select Rafael)
            <small>Same deterministic path, answered in Portuguese over Rafael's synthetic records.</small>
          </button>
        </div>
      </aside>

      <section class="panel workbench">
        <h2>Customer support workbench</h2>
        <label for="message">Customer message</label>
        <textarea id="message" placeholder="Start a session, then send a customer message…"></textarea>
        <button id="send" disabled>Send to local API</button>
        <div class="conversation" id="conversation">
          <div class="empty">Start a session and run one of the demo scenarios.</div>
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

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

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
      if (route === 'HANDOFF') return 'handoff';
      return '';
    }

    function routeExplanation(route) {
      if (route === 'ANSWER') {
        return 'Verified synthetic records matched the supported customer request.';
      }
      if (route === 'CLARIFY') {
        return 'More than one verified record matched; the customer is asked to choose.';
      }
      if (route === 'ESCALATE') {
        return 'The customer reported unauthorized activity, so the demo creates a stored support ticket. This is not fraud detection.';
      }
      if (route === 'ABSTAIN') {
        return 'The local rules do not support this request, so the system does not invent an answer.';
      }
      if (route === 'HANDOFF') {
        return 'The customer explicitly requested support, so the API returned stored ticket evidence.';
      }
      return '';
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
        els.conversation.innerHTML = '<div class="empty">Start a session and run one of the demo scenarios.</div>';
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
        const intent = response.intent && response.intent !== 'unknown' ? response.intent : '';
        const explanation = routeExplanation(route);
        return `
          <article class="turn">
            <header class="turn-header">
              <div class="pill-row">
                <span class="pill ${routeClass(route)}">${escapeHtml(route)}</span>
                ${intent ? `<span class="pill">${escapeHtml(intent)}</span>` : ''}
                ${response.synthetic_data ? '<span class="pill">synthetic data</span>' : ''}
              </div>
              ${response.escalation_ticket_id ? `<span class="pill escalate">ticket ${escapeHtml(response.escalation_ticket_id)}</span>` : ''}
            </header>
            <div class="turn-body">
              ${turn.message ? `<div class="user-text"><strong>Customer:</strong> ${escapeHtml(turn.message)}</div>` : ''}
              <div class="answer-text">${escapeHtml(response.response_text || turn.text || '')}</div>
              ${explanation ? `<div class="route-explanation">${escapeHtml(explanation)}</div>` : ''}
              ${response.reason_codes?.length ? `<div class="pill-row">${response.reason_codes.map((reason) => `<span class="pill">${escapeHtml(reason)}</span>`).join('')}</div>` : ''}
              ${candidates.length ? `<div class="record"><strong>Clarification candidates</strong><div>${candidates.map(escapeHtml).join(', ')}</div></div>` : ''}
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
        <strong>${escapeHtml(state.session.display_name)}</strong><br>
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
        els.llmConnected.textContent = String(ready.llm_connected);
      } catch (error) {
        els.readyStatus.textContent = 'not_ready';
        els.dataMode.textContent = 'unknown';
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
      renderSession();
      renderConversation();
    }

    async function sendTurn() {
      setError('');
      const message = els.message.value.trim();
      if (!message) return;
      if (state.session && els.persona.value !== state.session.persona_id) {
        setError('The selected persona differs from the active session. Click "Start new demo session" before sending.');
        return;
      }
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
      const handoffText = response.persisted && response.verified
        ? `Support ticket created (persisted: ${response.persisted}, verified: ${response.verified}). Ticket: ${response.ticket_id}`
        : `Handoff response received (persisted: ${response.persisted}, verified: ${response.verified}).${response.ticket_id ? ` Ticket: ${response.ticket_id}` : ''}`;
      state.turns.unshift({
        kind: 'HANDOFF',
        text: handoffText,
        response: {
          route: 'HANDOFF',
          intent: 'customer_requested_support_handoff',
          response_text: handoffText,
          escalation_ticket_id: response.ticket_id,
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
      button.addEventListener('click', () => {
        els.message.value = button.dataset.message || '';
        if (button.dataset.persona) {
          els.persona.value = button.dataset.persona;
        }
        if (button.dataset.persona === 'rafael') {
          els.language.value = '';
        }
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
