from __future__ import annotations


def render_challenge_ui(*, llm_connected: bool) -> str:
    """Return the judge-facing full challenge-data shell."""

    interpreter = (
        "OpenAI GPT-6 Luna · deterministic policy authority retained"
        if llm_connected
        else "Deterministic interpreter · deterministic policy authority retained"
    )
    mode_badge = "LIVE LLM · FULL DATA" if llm_connected else "FULL DATA · LOCAL"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Proof of One — Full Challenge Data</title>
  <style>
    :root {{
      color-scheme: light;
      --ink:#111;
      --muted:#656565;
      --paper:#f4f1e8;
      --panel:#fffdf7;
      --line:#bdb7aa;
      --soft:#e9e4d8;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; background:var(--paper); color:var(--ink);
      font-family:Arial,Helvetica,sans-serif;
    }}
    button,input,select,textarea {{ font:inherit; }}
    button {{
      border:1px solid var(--ink); background:var(--ink); color:#fff;
      padding:.7rem .85rem; cursor:pointer; font-weight:700;
    }}
    button.secondary {{ background:var(--panel); color:var(--ink); }}
    button:disabled {{ opacity:.35; cursor:not-allowed; }}
    input,select,textarea {{
      width:100%; border:1px solid var(--line); background:#fff;
      color:var(--ink); padding:.68rem;
    }}
    textarea {{ min-height:118px; resize:vertical; }}
    .page {{ max-width:1500px; margin:0 auto; padding:20px; }}
    .header {{
      border:2px solid var(--ink); background:var(--panel);
      padding:20px 22px; display:flex; align-items:flex-start;
      justify-content:space-between; gap:24px;
    }}
    .eyebrow {{ font-size:.74rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; }}
    h1 {{ margin:.25rem 0 .35rem; font-size:2rem; letter-spacing:-.035em; }}
    .sub {{ max-width:900px; color:var(--muted); line-height:1.45; }}
    .badge {{
      white-space:nowrap; border:1px solid var(--ink); padding:.45rem .6rem;
      font-size:.72rem; font-weight:800; letter-spacing:.08em;
    }}
    .boundary {{
      margin-top:10px; border:1px solid var(--ink); background:var(--ink);
      color:#fff; padding:9px 12px; font-size:.78rem; font-weight:700;
      letter-spacing:.02em;
    }}
    .grid {{
      display:grid; grid-template-columns:minmax(330px,420px) minmax(0,1fr);
      gap:14px; margin-top:14px;
    }}
    .panel {{ border:1px solid var(--line); background:var(--panel); padding:16px; }}
    .panel h2 {{
      margin:0 0 12px; font-size:.9rem; letter-spacing:.08em; text-transform:uppercase;
    }}
    .field {{ margin-bottom:12px; }}
    .field label {{
      display:block; margin-bottom:5px; font-size:.72rem; font-weight:800;
      letter-spacing:.07em; text-transform:uppercase;
    }}
    .row {{ display:flex; gap:8px; }}
    .row > * {{ flex:1; }}
    .meta {{
      padding:10px; border:1px solid var(--line); background:#fff;
      font-size:.8rem; line-height:1.45; min-height:48px;
    }}
    .coverage {{
      display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:7px;
      margin-top:8px;
    }}
    .metric {{
      border:1px solid var(--line); background:#fff; padding:8px;
      min-width:0;
    }}
    .metric strong {{ display:block; font-size:1rem; }}
    .metric span {{ font-size:.67rem; color:var(--muted); text-transform:uppercase; }}
    .signal {{
      border:2px solid var(--ink); background:var(--panel); padding:18px;
      min-height:250px;
    }}
    .signal-head {{
      display:flex; align-items:center; justify-content:space-between; gap:16px;
      border-bottom:1px solid var(--line); padding-bottom:12px; margin-bottom:14px;
    }}
    .route {{ font-size:2.3rem; font-weight:900; letter-spacing:-.045em; }}
    .lamp {{
      width:26px; height:26px; border:2px solid var(--ink); border-radius:50%;
      background:transparent;
    }}
    .lamp.on {{ background:var(--ink); }}
    .response {{
      white-space:pre-wrap; line-height:1.55; padding:14px;
      border:1px solid var(--line); background:#fff; min-height:90px;
    }}
    .evidence {{
      display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
      gap:8px; margin-top:12px;
    }}
    .evidence div {{ border:1px solid var(--line); padding:9px; background:#fff; min-height:62px; }}
    .evidence b {{ display:block; font-size:.65rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); margin-bottom:5px; }}
    .history {{ margin-top:14px; }}
    .history-item {{ border-top:1px solid var(--line); padding:10px 0; font-size:.82rem; }}
    .error {{ min-height:22px; color:#7d1616; font-size:.8rem; margin-top:8px; }}
    .micro {{ font-size:.72rem; color:var(--muted); line-height:1.45; }}
    @media (max-width:900px) {{
      .grid {{ grid-template-columns:1fr; }}
      .coverage,.evidence {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .header {{ flex-direction:column; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="header">
      <div>
        <div class="eyebrow">Proof of One</div>
        <h1>Full challenge-data signal box</h1>
        <div class="sub">
          Search a challenge customer by ID, replay a provided customer message or
          type a new Spanish/Portuguese request, and inspect the deterministic route
          and evidence returned from customer-scoped read-only records.
        </div>
      </div>
      <div class="badge">{mode_badge}</div>
    </section>
    <div class="boundary">
      Full challenge data · read-only · customer-scoped · language auto-detected ·
      deterministic route authority · not fraud detection · not production/pilot-ready
    </div>

    <section class="grid">
      <aside>
        <div class="panel">
          <h2>Challenge data</h2>
          <div id="coverageStatus" class="micro">Loading coverage…</div>
          <div id="coverage" class="coverage"></div>
        </div>

        <div class="panel" style="margin-top:14px">
          <h2>Customer controls</h2>
          <div class="field">
            <label for="customerQuery">Customer ID</label>
            <div class="row">
              <input id="customerQuery" placeholder="e.g. customer ID prefix">
              <button id="searchCustomer" type="button">Search</button>
            </div>
          </div>
          <div class="field">
            <label for="customerSelect">Matching customer</label>
            <select id="customerSelect"></select>
          </div>
          <button id="startSession" type="button">Start scoped session</button>
          <div id="sessionBox" class="meta" style="margin-top:10px">No active challenge session.</div>
          <div id="error" class="error"></div>
        </div>

        <div class="panel" style="margin-top:14px">
          <h2>Provided messages</h2>
          <div class="field">
            <label for="providedMessage">Customer transcript</label>
            <select id="providedMessage" disabled></select>
          </div>
          <div class="row">
            <button id="useMessage" class="secondary" type="button" disabled>Use selected message</button>
            <button id="loadMore" class="secondary" type="button" disabled>Load more</button>
          </div>
          <p class="micro">
            Messages are loaded only for the active customer. Agent text and direct
            customer identifiers are not exposed in this selector.
          </p>
        </div>
      </aside>

      <section>
        <div class="panel">
          <h2>Customer message</h2>
          <div class="field">
            <textarea id="message" placeholder="Replay a provided message or type a new Spanish/Portuguese request."></textarea>
          </div>
          <div class="row">
            <button id="send" type="button" disabled>Set route · send message</button>
            <button id="handoff" class="secondary" type="button" disabled>Handoff lane</button>
            <button id="revoke" class="secondary" type="button" disabled>Revoke session</button>
          </div>
        </div>

        <div class="signal" style="margin-top:14px">
          <div class="signal-head">
            <div>
              <div class="eyebrow">Interlocking · deterministic policy</div>
              <div id="route" class="route">WAITING</div>
              <div id="interpreter" class="micro">Interpreter: {interpreter}</div>
            </div>
            <div id="lamp" class="lamp"></div>
          </div>
          <div id="response" class="response">Start a scoped customer session, then send a provided or custom message.</div>
          <div id="evidence" class="evidence"></div>
        </div>

        <div class="panel history">
          <h2>Session turns</h2>
          <div id="turns" class="micro">No turns yet.</div>
        </div>
      </section>
    </section>
  </main>

<script>
(() => {{
  const state = {{
    customers: [],
    customer: null,
    session: null,
    messages: [],
    messageOffset: 0,
    lastResponse: null,
    turns: []
  }};

  const els = {{
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
    route: document.getElementById('route'),
    lamp: document.getElementById('lamp'),
    response: document.getElementById('response'),
    evidence: document.getElementById('evidence'),
    turns: document.getElementById('turns')
  }};

  function setError(message) {{ els.error.textContent = message || ''; }}

  async function api(path, options = {{}}) {{
    const headers = Object.assign({{'Content-Type': 'application/json'}}, options.headers || {{}});
    if (state.session) headers['X-Demo-Session'] = state.session.session_id;
    const response = await fetch(path, Object.assign({{}}, options, {{headers}}));
    if (!response.ok) {{
      let detail = response.statusText;
      try {{
        const body = await response.json();
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }} catch (_) {{}}
      throw new Error(detail || ('HTTP ' + response.status));
    }}
    if (response.status === 204) return null;
    return response.json();
  }}

  function clearChildren(node) {{
    while (node.firstChild) node.removeChild(node.firstChild);
  }}

  function option(value, text) {{
    const node = document.createElement('option');
    node.value = value;
    node.textContent = text;
    return node;
  }}

  function renderCoverage(data) {{
    clearChildren(els.coverage);
    const counts = data?.table_counts || {{}};
    const preferred = [
      ['customers','Customers'],
      ['transactions','Transactions'],
      ['call_transcripts','Messages'],
      ['call_center_interactions','Interactions'],
      ['complaints','Complaints'],
      ['digital_events','Digital events']
    ];
    for (const [key,label] of preferred) {{
      if (!(key in counts)) continue;
      const metric = document.createElement('div');
      metric.className = 'metric';
      const strong = document.createElement('strong');
      strong.textContent = Number(counts[key]).toLocaleString();
      const span = document.createElement('span');
      span.textContent = label;
      metric.append(strong, span);
      els.coverage.appendChild(metric);
    }}
    els.coverageStatus.textContent = data?.full_challenge_data
      ? 'Full challenge artifact available server-side.'
      : 'Full challenge artifact unavailable.';
  }}

  function renderCustomers() {{
    clearChildren(els.customerSelect);
    if (!state.customers.length) {{
      els.customerSelect.appendChild(option('', 'No matching customer IDs'));
      return;
    }}
    for (const customer of state.customers) {{
      const label = customer.customer_id + ' · ' +
        (customer.country || 'country n/a') + ' · ' +
        customer.transcript_count + ' messages';
      els.customerSelect.appendChild(option(customer.customer_id, label));
    }}
  }}

  function renderSession() {{
    if (!state.session) {{
      els.sessionBox.textContent = 'No active challenge session.';
      els.send.disabled = true;
      els.handoff.disabled = true;
      els.revoke.disabled = true;
      els.providedMessage.disabled = true;
      els.useMessage.disabled = true;
      els.loadMore.disabled = true;
      return;
    }}
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
  }}

  function renderMessages() {{
    clearChildren(els.providedMessage);
    if (!state.messages.length) {{
      els.providedMessage.appendChild(option('', 'No provided customer messages'));
      renderSession();
      return;
    }}
    state.messages.forEach((message, index) => {{
      const preview = message.customer_text.length > 92
        ? message.customer_text.slice(0, 89) + '…'
        : message.customer_text;
      els.providedMessage.appendChild(
        option(String(index), (message.process_date || 'date n/a') + ' · ' + preview)
      );
    }});
    renderSession();
  }}

  function evidenceItem(label, value) {{
    const box = document.createElement('div');
    const title = document.createElement('b');
    title.textContent = label;
    const body = document.createTextNode(value == null ? '—' : String(value));
    box.append(title, body);
    return box;
  }}

  function renderEvidence(response) {{
    clearChildren(els.evidence);
    if (!response) {{
      for (const label of ['Route','Intent','Language','Interpretation','Reference','Control']) {{
        els.evidence.appendChild(evidenceItem(label, 'waiting'));
      }}
      return;
    }}
    const e = response.decision_evidence || {{}};
    const verification = Array.isArray(e.verification_codes)
      ? e.verification_codes.join(' · ')
      : '—';
    const values = [
      ['Route', response.route],
      ['Intent', response.intent],
      ['Language', e.language ? e.language.toUpperCase() : '—'],
      ['Interpretation', e.interpretation_status],
      ['Reference', e.reference_status],
      ['Control', e.controlling_reason || 'all checks clear'],
      ['Action', e.action],
      ['Execution', e.execution_status],
      ['Verification', verification]
    ];
    for (const [label,value] of values) els.evidence.appendChild(evidenceItem(label,value));
  }}

  function renderResponse(response) {{
    state.lastResponse = response;
    els.route.textContent = response?.route || 'WAITING';
    els.lamp.classList.toggle('on', Boolean(response?.route));
    els.response.textContent = response?.response_text ||
      'Start a scoped customer session, then send a provided or custom message.';
    renderEvidence(response);
  }}

  function renderTurns() {{
    clearChildren(els.turns);
    if (!state.turns.length) {{
      els.turns.textContent = 'No turns yet.';
      return;
    }}
    for (const turn of state.turns) {{
      const item = document.createElement('div');
      item.className = 'history-item';
      item.textContent = turn.route + ' · ' + turn.message;
      els.turns.appendChild(item);
    }}
  }}

  async function loadCoverage() {{
    renderCoverage(await api('/api/challenge/coverage', {{headers: {{}}}}));
  }}

  async function searchCustomers() {{
    setError('');
    const query = encodeURIComponent(els.customerQuery.value.trim());
    state.customers = await api('/api/challenge/customers?query=' + query + '&limit=20', {{headers: {{}}}});
    renderCustomers();
  }}

  async function loadMessages(reset = true) {{
    if (!state.session) return;
    if (reset) {{
      state.messages = [];
      state.messageOffset = 0;
    }}
    const rows = await api(
      '/api/challenge/customers/' + encodeURIComponent(state.session.customer_id) +
      '/messages?limit=25&offset=' + state.messageOffset,
      {{headers: {{}}}}
    );
    state.messages.push(...rows);
    state.messageOffset += rows.length;
    renderMessages();
    els.loadMore.disabled = rows.length < 25;
  }}

  async function startSession() {{
    setError('');
    const customerId = els.customerSelect.value;
    if (!customerId) throw new Error('Choose a challenge customer first.');
    state.session = await api('/api/challenge/sessions', {{
      method:'POST',
      headers: {{}},
      body: JSON.stringify({{customer_id: customerId}})
    }});
    state.turns = [];
    state.lastResponse = null;
    renderResponse(null);
    renderTurns();
    await loadMessages(true);
    renderSession();
  }}

  function useSelectedMessage() {{
    const index = Number(els.providedMessage.value);
    const row = state.messages[index];
    if (row) els.message.value = row.customer_text;
  }}

  async function sendTurn() {{
    setError('');
    const message = els.message.value.trim();
    if (!message) return;
    const response = await api('/api/customer/turn', {{
      method:'POST',
      body: JSON.stringify({{message}})
    }});
    state.turns.unshift({{message, route:response.route}});
    renderResponse(response);
    renderTurns();
  }}

  async function handoff() {{
    setError('');
    const response = await api('/api/customer/handoff', {{
      method:'POST',
      body:'{{}}'
    }});
    const mapped = {{
      route:'HANDOFF',
      intent:'customer_requested_support_handoff',
      response_text: response.persisted && response.verified
        ? 'Support ticket persisted and read-back verified. Ticket: ' + response.ticket_id
        : 'Support ticket response received.',
      decision_evidence:{{
        language: state.session?.language,
        interpretation_status:'not invoked',
        reference_status:'not applicable',
        controlling_reason:'customer requested support',
        action:'create support ticket',
        execution_status: response.persisted ? 'completed' : 'unknown',
        verification_codes:[
          response.persisted ? 'ticket persisted' : 'persistence unverified',
          response.verified ? 'read-back verified' : 'read-back unverified'
        ]
      }}
    }};
    state.turns.unshift({{message:'Customer requested support handoff',route:'HANDOFF'}});
    renderResponse(mapped);
    renderTurns();
  }}

  async function revoke() {{
    await api('/api/demo/session', {{method:'DELETE',body:'{{}}'}});
    state.session = null;
    state.messages = [];
    state.messageOffset = 0;
    state.turns = [];
    renderMessages();
    renderSession();
    renderResponse(null);
    renderTurns();
  }}

  els.searchCustomer.addEventListener('click', () => searchCustomers().catch(e => setError(e.message)));
  els.customerQuery.addEventListener('keydown', (event) => {{
    if (event.key === 'Enter') searchCustomers().catch(e => setError(e.message));
  }});
  els.startSession.addEventListener('click', () => startSession().catch(e => setError(e.message)));
  els.useMessage.addEventListener('click', useSelectedMessage);
  els.loadMore.addEventListener('click', () => loadMessages(false).catch(e => setError(e.message)));
  els.send.addEventListener('click', () => sendTurn().catch(e => setError(e.message)));
  els.handoff.addEventListener('click', () => handoff().catch(e => setError(e.message)));
  els.revoke.addEventListener('click', () => revoke().catch(e => setError(e.message)));

  renderSession();
  renderEvidence(null);
  renderTurns();
  Promise.all([loadCoverage(), searchCustomers()]).catch(e => setError(e.message));
}})();
</script>
</body>
</html>"""
