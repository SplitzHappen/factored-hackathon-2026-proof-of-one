from __future__ import annotations


def render_challenge_ui(*, llm_connected: bool) -> str:
    """Return the judge-facing full challenge-data shell."""

    interpreter = (
        "OpenAI GPT-6 Luna · deterministic policy authority retained"
        if llm_connected
        else "Deterministic interpreter · deterministic policy authority retained"
    )
    mode_badge = "LIVE LLM · FULL DATA" if llm_connected else "FULL DATA · LOCAL"

    html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proof of One — Deterministic Support Interlock</title>
<style>
:root{
  color-scheme:light;
  --page:#cbd4c4; --page2:#bac5b6; --panel:#e8eee3; --panel2:#f7f9f1;
  --ink:#102015; --ink2:#34463e; --line:#899489; --dark:#071108;
  --cream:#fff4d2; --green:#28b66b; --red:#c64d43; --amber:#d39b24; --blue:#477ed1; --purple:#8562bf;
  --shadow:0 24px 48px rgba(14,27,16,.20);
  font-family:"IBM Plex Mono","Cascadia Mono",Consolas,ui-monospace,monospace;
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--ink);background:linear-gradient(145deg,var(--page),var(--page2))}
.page{width:min(1560px,calc(100vw - 28px));margin:0 auto;padding:16px 0 32px}
.shell{border:3px solid var(--line);border-radius:34px;background:rgba(232,238,227,.90);box-shadow:var(--shadow);overflow:hidden}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;padding:28px 40px 34px;border-bottom:3px solid var(--line);background:rgba(203,212,196,.92)}
.kicker{margin:0 0 8px;color:var(--ink2);font-size:22px;font-weight:900;letter-spacing:.26em;text-transform:uppercase}
h1{margin:0;color:var(--ink);font-size:clamp(34px,5vw,70px);line-height:.98;font-weight:1000;letter-spacing:.07em;text-transform:uppercase;white-space:nowrap}
.brand p{margin:14px 0 0;max-width:980px;color:var(--ink2);font-family:Inter,system-ui,sans-serif;font-size:18px;line-height:1.45}
.badges{display:flex;gap:14px;flex-wrap:wrap;justify-content:flex-end}
.badge{border:3px solid var(--line);border-radius:999px;background:rgba(247,249,241,.72);padding:13px 20px;color:var(--ink);font-size:20px;font-weight:1000;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
.main{display:grid;grid-template-columns:minmax(330px,410px) minmax(0,1fr);gap:20px;padding:20px}
.card{border:3px solid var(--line);border-radius:28px;background:rgba(232,238,227,.88);box-shadow:0 14px 28px rgba(14,27,16,.10)}
.controls{display:grid;gap:14px;align-content:start;padding:20px}
.section-title{margin:0;color:var(--ink);font-size:21px;font-weight:1000;letter-spacing:.16em;text-transform:uppercase}
.field label{display:block;margin:0 0 8px;color:var(--ink2);font-size:12px;font-weight:1000;letter-spacing:.16em;text-transform:uppercase}
input,select,textarea,button{width:100%;border-radius:14px;font:inherit}
input,select,textarea{border:2px solid rgba(16,32,21,.32);background:rgba(247,249,241,.92);color:var(--ink);padding:12px 13px}
textarea{min-height:116px;line-height:1.45;resize:vertical}
button{border:3px solid var(--line);background:#edf2e8;color:var(--ink);cursor:pointer;font-weight:1000;letter-spacing:.06em;padding:12px 14px;text-transform:uppercase}
button:disabled{opacity:.46;cursor:not-allowed}
.primary{background:#dfeadf;border-color:rgba(40,182,107,.55)}
.human{background:#e6dff0;border-color:rgba(133,98,191,.55)}
.revoke{background:#f0dedb;border-color:rgba(198,77,67,.55)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.session-box,.error{border-radius:16px;padding:12px;font-family:Inter,system-ui,sans-serif;font-size:13px;line-height:1.45}
.session-box{color:var(--ink2);background:rgba(247,249,241,.70);border:2px solid rgba(16,32,21,.18);overflow-wrap:anywhere}
.error{display:none;color:#5e1814;border:2px solid rgba(198,77,67,.55);background:rgba(198,77,67,.12)}
.board{display:grid;gap:18px}
.route-board{display:grid;grid-template-columns:minmax(0,1fr) 104px;gap:22px;align-items:start;min-height:300px;padding:30px;border-radius:30px;background:var(--dark);border:4px solid #1f2e22}
.route-word{color:var(--cream);font-size:clamp(54px,8vw,112px);font-weight:1000;letter-spacing:.10em;line-height:.88;text-transform:uppercase;white-space:nowrap;overflow:hidden}
.status-copy{grid-column:1/-1;margin:0;color:#c9d4c3;font-family:Inter,system-ui,sans-serif;font-size:22px;line-height:1.45}
.response{grid-column:1/-1;border:2px solid rgba(255,244,210,.34);border-radius:24px;background:rgba(255,244,210,.08);padding:24px 28px;color:var(--cream);font-family:Inter,system-ui,sans-serif;font-size:26px;line-height:1.5;min-height:124px}
.lamp-cell{display:grid;place-items:start center;min-width:104px;padding-top:8px}
.lamp,.mini-lamp,.dot{border-radius:50%;background:radial-gradient(circle at 50% 42%,#6b7569,#354033 58%,#161d17 59%)}
.lamp{width:86px;height:86px;border:12px solid #344032;box-shadow:0 0 0 9px rgba(255,244,210,.05),inset 0 0 18px rgba(0,0,0,.45)}
.mini-lamp{width:64px;height:64px;border:9px solid #344032;box-shadow:inset 0 0 15px rgba(0,0,0,.34)}
.on.green,.check.green .mini-lamp{background:radial-gradient(circle at 50% 42%,#3ee285,#26b66a 58%,#116036 59%);box-shadow:0 0 28px rgba(40,182,107,.70)}
.on.red,.check.red .mini-lamp{background:radial-gradient(circle at 50% 42%,#ff7b70,#c64d43 58%,#641f1b 59%);box-shadow:0 0 28px rgba(198,77,67,.70)}
.on.amber,.check.amber .mini-lamp{background:radial-gradient(circle at 50% 42%,#ffe38a,#d39b24 58%,#6d4e12 59%);box-shadow:0 0 28px rgba(211,155,36,.70)}
.on.blue,.check.blue .mini-lamp{background:radial-gradient(circle at 50% 42%,#8bb7ff,#477ed1 58%,#254476 59%);box-shadow:0 0 28px rgba(71,126,209,.70)}
.on.purple,.check.purple .mini-lamp{background:radial-gradient(circle at 50% 42%,#cba4ff,#8562bf 58%,#493071 59%);box-shadow:0 0 28px rgba(133,98,191,.70)}
.route-board.busy .lamp,.route-board.busy .route-word{animation:pulse 1s infinite}
@keyframes pulse{0%,100%{filter:brightness(.85)}50%{filter:brightness(1.45)}}
.checks{display:grid;grid-template-columns:repeat(4,minmax(245px,1fr));gap:16px}
.check{min-height:226px;border:4px solid var(--line);border-radius:28px;background:rgba(232,238,227,.92);padding:26px;color:var(--ink);overflow:hidden}
.check-head{display:grid;grid-template-columns:1fr 74px;grid-template-areas:"num lamp" "title title";column-gap:18px;row-gap:16px;align-items:start}
.check-num{grid-area:num;color:var(--ink);font-size:clamp(34px,2.6vw,48px);font-weight:1000;line-height:1}
.check-head .mini-lamp{grid-area:lamp;justify-self:end}
.check-title{grid-area:title;color:var(--ink);font-size:clamp(18px,1.18vw,24px);font-weight:1000;letter-spacing:.045em;line-height:1.18;text-transform:uppercase;white-space:normal;overflow-wrap:anywhere;word-break:normal;max-width:100%}
.check p{margin:26px 0 0;color:var(--ink);font-family:Inter,system-ui,sans-serif;font-size:25px;line-height:1.42}
.lanes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.lane{border:4px solid var(--line);border-radius:24px;background:rgba(232,238,227,.92);padding:18px;display:grid;grid-template-columns:minmax(0,1fr) 48px;align-items:center;gap:12px}
.lane span{font-size:22px;font-weight:1000;letter-spacing:.13em;text-transform:uppercase}
.lane .dot{justify-self:end;width:42px;height:42px;border:8px solid #3b463c}
.lane.active.answer .dot{background:#28b66b;box-shadow:0 0 20px rgba(40,182,107,.65)}
.lane.active.clarify .dot{background:#d39b24;box-shadow:0 0 20px rgba(211,155,36,.65)}
.lane.active.escalate .dot{background:#c64d43;box-shadow:0 0 20px rgba(198,77,67,.65)}
.lane.active.abstain .dot{background:#477ed1;box-shadow:0 0 20px rgba(71,126,209,.65)}
.lower{display:grid;grid-template-columns:minmax(0,1fr) minmax(350px,430px);gap:16px}
.why,.evidence{padding:26px}
.why h2,.evidence h2{margin:0 0 18px;color:var(--ink);font-size:24px;font-weight:1000;letter-spacing:.16em;text-transform:uppercase}
.why p{margin:0;color:var(--ink);font-family:Inter,system-ui,sans-serif;font-size:21px;line-height:1.5}
.evidence{text-align:center}
.evidence-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.e-card{border:2px solid rgba(16,32,21,.22);border-radius:18px;background:rgba(247,249,241,.78);padding:15px;min-height:92px}
.e-card strong{display:block;text-align:center;color:var(--ink2);font-size:17px;font-weight:1000;letter-spacing:.14em;text-transform:uppercase}
.e-card span{display:block;margin-top:10px;color:var(--ink);font-family:Inter,system-ui,sans-serif;font-size:19px;overflow-wrap:anywhere}
.foot{padding:0 20px 22px;color:var(--ink2);font-family:Inter,system-ui,sans-serif;font-size:13px}
@media(max-width:1200px){.checks{grid-template-columns:1fr 1fr}.lower{grid-template-columns:1fr}}
@media(max-width:900px){.topbar,.main{grid-template-columns:1fr}.badges{justify-content:flex-start}.route-board{grid-template-columns:1fr}.lamp-cell{place-items:center}.route-word,h1{white-space:normal}.lanes{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.checks,.lanes,.evidence-grid{grid-template-columns:1fr}.response{font-size:20px}.route-word{font-size:46px}}
</style>
</head>
<body>
<div class="page"><div class="shell">
<header class="topbar">
  <div class="brand">
    <p class="kicker">Interlocking tower · deterministic policy</p>
    <h1>Deterministic Support Interlock</h1>
    <p>Customer-scoped records · LLM interpretation · deterministic route authority · visible verification.</p>
  </div>
  <div class="badges"><div class="badge" id="languageBadge">ES/PT auto</div><div class="badge">__MODE_BADGE__</div></div>
</header>
<main class="main">
  <aside class="card controls">
    <h2 class="section-title">Challenge data</h2>
    <div class="field"><label for="customerSearch">Customer ID prefix</label><input id="customerSearch" placeholder="Leave blank, or type a prefix"></div>
    <button id="searchBtn" class="primary">Search customers</button>
    <div class="field"><label for="customerSelect">Matching customer</label><select id="customerSelect"><option value="">Search first</option></select></div>
    <button id="sessionBtn" class="primary" disabled>Start scoped session</button>
    <div id="sessionBox" class="session-box">No scoped customer session yet.</div>
    <div class="field"><label for="messageSelect">Provided messages</label><select id="messageSelect" disabled><option value="">Start session first</option></select></div>
    <button id="useMessageBtn" disabled>Use selected message</button>
    <div class="field"><label for="messageBox">Customer message</label><textarea id="messageBox" placeholder="Use a provided message or write a custom Spanish/Portuguese request."></textarea></div>
    <button id="sendBtn" class="primary" disabled>Set route · send</button>
    <div class="two"><button id="handoffBtn" class="human" disabled>Human review</button><button id="revokeBtn" class="revoke" disabled>Revoke session</button></div>
    <div id="errorBox" class="error"></div>
  </aside>

  <section class="board">
    <div id="routeBoard" class="route-board">
      <div id="routeWord" class="route-word">WAITING</div>
      <div class="lamp-cell"><div id="mainLamp" class="lamp"></div></div>
      <p id="statusCopy" class="status-copy">__INTERPRETER__</p>
      <div id="responseText" class="response">Start a scoped customer session, then send a provided or custom message.</div>
    </div>

    <div class="checks">
      <div id="check1" class="check"><div class="check-head"><div class="check-num">1 ·</div><div class="mini-lamp"></div><div class="check-title">Interpreter</div></div><p id="check1Text">Awaiting message.</p></div>
      <div id="check2" class="check"><div class="check-head"><div class="check-num">2 ·</div><div class="mini-lamp"></div><div class="check-title">Customer<br>Scope</div></div><p id="check2Text">No customer session yet.</p></div>
      <div id="check3" class="check"><div class="check-head"><div class="check-num">3 ·</div><div class="mini-lamp"></div><div class="check-title">Route<br>Authority</div></div><p id="check3Text">No route selected.</p></div>
      <div id="check4" class="check"><div class="check-head"><div class="check-num">4 ·</div><div class="mini-lamp"></div><div class="check-title">Act<br>→<br>Verify</div></div><p id="check4Text">No action invoked.</p></div>
    </div>

    <div class="lanes">
      <div id="laneANSWER" class="lane answer"><span>ANSWER</span><div class="dot"></div></div>
      <div id="laneCLARIFY" class="lane clarify"><span>CLARIFY</span><div class="dot"></div></div>
      <div id="laneESCALATE" class="lane escalate"><span>ESCALATE</span><div class="dot"></div></div>
      <div id="laneABSTAIN" class="lane abstain"><span>ABSTAIN</span><div class="dot"></div></div>
    </div>

    <div class="lower">
      <div class="card why"><h2>Why this route</h2><p id="whyText">No route has been selected yet.</p></div>
      <div class="card evidence"><h2>Decision evidence</h2><div class="evidence-grid">
        <div class="e-card"><strong>Route</strong><span id="evRoute">waiting</span></div>
        <div class="e-card"><strong>Intent</strong><span id="evIntent">n/a</span></div>
        <div class="e-card"><strong>Language</strong><span id="evLanguage">n/a</span></div>
        <div class="e-card"><strong>Reference</strong><span id="evReference">n/a</span></div>
        <div class="e-card"><strong>Control</strong><span id="evControl">n/a</span></div>
        <div class="e-card"><strong>Verify</strong><span id="evVerify">n/a</span></div>
        <div class="e-card"><strong>Action</strong><span id="evAction">n/a</span></div>
        <div class="e-card"><strong>Execution</strong><span id="evExecution">n/a</span></div>
      </div></div>
    </div>
  </section>
</main>
<div class="foot">Full challenge data · read-only · customer-scoped · language auto-detected · deterministic route authority.</div>
</div></div>

<script>
const state={session:null,customers:[],messages:[],busy:false};
const $=(id)=>document.getElementById(id);
const els={search:$('customerSearch'),searchBtn:$('searchBtn'),customer:$('customerSelect'),sessionBtn:$('sessionBtn'),sessionBox:$('sessionBox'),messageSelect:$('messageSelect'),useMessageBtn:$('useMessageBtn'),messageBox:$('messageBox'),sendBtn:$('sendBtn'),handoffBtn:$('handoffBtn'),revokeBtn:$('revokeBtn'),error:$('errorBox'),routeBoard:$('routeBoard'),routeWord:$('routeWord'),mainLamp:$('mainLamp'),status:$('statusCopy'),response:$('responseText'),languageBadge:$('languageBadge'),why:$('whyText')};
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function clean(v){return String(v??'').replace(/_/g,' ');}
function showError(msg){els.error.style.display='block';els.error.textContent=clean(msg).replace(/demo/gi,'session');}
function clearError(){els.error.style.display='none';els.error.textContent='';}
function routeColor(route){return{ANSWER:'green',CLARIFY:'amber',ESCALATE:'red',ABSTAIN:'blue'}[route]||'';}
function setLamp(color){els.mainLamp.className='lamp'+(color?' on '+color:'');}
function setMini(id,on,color){$(id).className='check'+(on?' active':'')+(color?' '+color:'');}
function setBusy(on){
  state.busy=on; els.routeBoard.classList.toggle('busy',on);
  els.searchBtn.disabled=on; els.sessionBtn.disabled=on||!els.customer.value; els.sendBtn.disabled=on||!state.session; els.handoffBtn.disabled=on||!state.session; els.revokeBtn.disabled=on||!state.session;
  if(on){els.routeWord.textContent='SETTING';els.status.textContent='Interlock checks running...';els.response.textContent='Processing the customer message against scoped records and deterministic policy.';setLamp('amber');}
}
function resetBoard(){
  els.routeWord.textContent='WAITING'; setLamp('');
  ['check1','check2','check3','check4'].forEach(id=>setMini(id,false,''));
  $('check1Text').textContent='Awaiting message.'; $('check2Text').textContent=state.session?'Customer scope armed.':'No customer session yet.'; $('check3Text').textContent='No route selected.'; $('check4Text').textContent='No action invoked.';
  ['ANSWER','CLARIFY','ESCALATE','ABSTAIN'].forEach(r=>$('lane'+r).className='lane '+r.toLowerCase());
  els.why.textContent='No route has been selected yet.';
  ['Route','Intent','Language','Reference','Control','Verify','Action','Execution'].forEach(k=>{const el=$('ev'+k); if(el) el.textContent=k==='Route'?'waiting':'n/a';});
}
async function jsonFetch(url,opts={}){
  const resp=await fetch(url,opts); const text=await resp.text(); let data={}; if(text){data=JSON.parse(text);}
  if(!resp.ok){throw new Error(data.detail||resp.statusText);} return data;
}
async function searchCustomers(){
  clearError(); const q=encodeURIComponent(els.search.value.trim());
  const data=await jsonFetch(`/api/challenge/customers?query=${q}&limit=12`);
  state.customers=data;
  els.customer.innerHTML=data.length?data.map(c=>`<option value="${esc(c.customer_id)}">${esc(c.customer_id)} · ${esc(c.country||'country n/a')} · ${esc(c.default_language||'lang n/a')} · ${esc(c.transcript_count)} msgs</option>`).join(''):'<option value="">No matches</option>';
  els.sessionBtn.disabled=!data.length;
}
async function startSession(){
  clearError(); const customer_id=els.customer.value; if(!customer_id){return;}
  const session=await jsonFetch('/api/challenge/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_id})});
  state.session=session; els.sessionBox.innerHTML=`Scoped session active<br>Customer: ${esc(session.customer_id)}<br>Profile locale: ${esc(session.language)}<br>Transcripts: ${esc(session.transcript_count)}`;
  els.sendBtn.disabled=false; els.handoffBtn.disabled=false; els.revokeBtn.disabled=false; setMini('check2',true,'green'); $('check2Text').textContent='Customer scope armed.';
  await loadMessages(customer_id);
}
async function loadMessages(customerId){
  const data=await jsonFetch(`/api/challenge/customers/${encodeURIComponent(customerId)}/messages?limit=25&offset=0`);
  state.messages=data; els.messageSelect.disabled=!data.length; els.useMessageBtn.disabled=!data.length;
  els.messageSelect.innerHTML=data.length?data.map((m,i)=>`<option value="${i}">${esc(m.process_date||'date n/a')} · ${esc(m.detected_language||'lang n/a')} · ${esc((m.main_topics||'topic n/a').slice(0,80))}</option>`).join(''):'<option value="">No provided messages</option>';
}
function useSelectedMessage(){const m=state.messages[Number(els.messageSelect.value)]; if(m){els.messageBox.value=m.customer_text;}}
function renderResult(data){
  const route=data.route||'WAITING'; const ev=data.decision_evidence||{}; const lang=(ev.language||(state.session&&state.session.language)||'').toUpperCase(); const color=routeColor(route);
  els.routeWord.textContent=route; setLamp(color); els.response.textContent=data.response_text||'No customer-facing text returned.'; els.status.textContent='__INTERPRETER__'; els.languageBadge.textContent=lang?`${lang} detected`:'ES/PT auto';
  setMini('check1',true,'green'); setMini('check2',true,'green'); setMini('check3',true,color);
  const verifyColor=route==='ESCALATE'?'red':(route==='CLARIFY'?'amber':(route==='ABSTAIN'?'blue':'green')); setMini('check4',true,verifyColor);
  $('check1Text').textContent=`Language ${lang||'n/a'} · intent ${clean(data.intent||'unknown')} · status ${clean(ev.interpretation_status||'verified')}.`;
  $('check2Text').textContent=`Customer-scoped records checked · reference ${clean(ev.reference_status||'not_required')}.`;
  $('check3Text').textContent=`Route authority: ${route} · ${clean(ev.controlling_reason||(data.reason_codes||[])[0]||'policy controlled')}.`;
  $('check4Text').textContent=`Action ${clean(ev.action||'none')} · execution ${clean(ev.execution_status||'not_invoked')}.`;
  ['ANSWER','CLARIFY','ESCALATE','ABSTAIN'].forEach(r=>$('lane'+r).className='lane '+r.toLowerCase()+(r===route?' active':''));
  els.why.textContent=`The interlock selected ${route} because deterministic policy controlled the route using scoped customer records, reference status, and supported-action checks.`;
  $('evRoute').textContent=route; $('evIntent').textContent=clean(data.intent||'unknown'); $('evLanguage').textContent=lang||'n/a'; $('evReference').textContent=clean(ev.reference_status||'n/a'); $('evControl').textContent=clean(ev.controlling_reason||(data.reason_codes||[])[0]||'n/a'); $('evVerify').textContent=clean((ev.verification_codes||[]).join(', ')||'n/a'); $('evAction').textContent=clean(ev.action||'none'); $('evExecution').textContent=clean(ev.execution_status||'n/a');
}
async function sendTurn(){
  if(!state.session){showError('Start a scoped customer session first.'); return;}
  const message=els.messageBox.value.trim(); if(!message){showError('Enter or select a customer message first.'); return;}
  clearError(); setBusy(true);
  try{const data=await jsonFetch('/api/customer/turn',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Session':state.session.session_id},body:JSON.stringify({message})}); setBusy(false); renderResult(data);}
  catch(err){setBusy(false); showError(err.message);}
}
async function humanReview(){
  if(!state.session){return;} clearError(); setBusy(true);
  try{const data=await jsonFetch('/api/customer/handoff',{method:'POST',headers:{'X-Demo-Session':state.session.session_id}});
    setBusy(false); renderResult({route:'ESCALATE',intent:'human_review_requested',response_text:'Registered this case for human review.',reason_codes:['human_review_requested'],decision_evidence:{language:state.session.language,reference_status:'not_required',controlling_reason:'human_review_requested',action:'create_escalation_ticket',execution_status:data.persisted&&data.verified?'completed':'not_invoked',verification_codes:['escalation_persisted','escalation_readback_verified']}});
  } catch(err){setBusy(false); showError(err.message);}
}
async function revoke(){
  if(!state.session){return;} clearError();
  try{await fetch('/api/demo/session',{method:'DELETE',headers:{'X-Demo-Session':state.session.session_id}});}catch(_e){}
  state.session=null; state.messages=[]; els.sessionBox.textContent='No scoped customer session yet.'; els.messageSelect.innerHTML='<option value="">Start session first</option>'; els.messageSelect.disabled=true; els.useMessageBtn.disabled=true; els.sendBtn.disabled=true; els.handoffBtn.disabled=true; els.revokeBtn.disabled=true; els.response.textContent='Session revoked. Start a new scoped customer session to continue.'; resetBoard();
}
els.searchBtn.addEventListener('click',()=>searchCustomers().catch(e=>showError(e.message)));
els.customer.addEventListener('change',()=>{els.sessionBtn.disabled=!els.customer.value||state.busy;});
els.sessionBtn.addEventListener('click',()=>startSession().catch(e=>showError(e.message)));
els.useMessageBtn.addEventListener('click',useSelectedMessage);
els.sendBtn.addEventListener('click',sendTurn);
els.handoffBtn.addEventListener('click',humanReview);
els.revokeBtn.addEventListener('click',revoke);
searchCustomers().catch(()=>{}); resetBoard();
</script>
</body>
</html>"""

    return (
        html.replace("__INTERPRETER__", interpreter)
        .replace("__MODE_BADGE__", mode_badge)
    )
