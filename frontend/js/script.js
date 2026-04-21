"use strict";
const API = window.location.protocol === "file:" ? "http://localhost:5000/api" : "/api";

// ─── Global State ────────────────────────────────────────────
const S = {
  score:0, qqs:[], qi:0, qc:0, qw:0, diff:"all",
  history:[], llmOn:false, sessionId:null, aiGenerated:false,
  svc:"mobile", selectedOp:null, selectedPlan:null, planType:"prepaid",
  myPlanOp:null, allAltPlans:[], currentPlan:null,
  _allLoadedPlans:[],
  user: null,
};

// ═══════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════
function showAuthModal() {
  const ov = document.getElementById("auth-overlay");
  if (ov) { ov.classList.remove("hidden"); ov.style.display = "flex"; }
}
function hideAuthModal() {
  const ov = document.getElementById("auth-overlay");
  if (ov) { ov.style.display = "none"; }
}

function switchAuthTab(tab) {
  document.getElementById("tab-login").classList.toggle("active",    tab === "login");
  document.getElementById("tab-register").classList.toggle("active", tab === "register");
  document.getElementById("auth-login-form").style.display    = tab === "login"    ? "block" : "none";
  document.getElementById("auth-register-form").style.display = tab === "register" ? "block" : "none";
  document.getElementById("login-error").style.display = "none";
  document.getElementById("reg-error").style.display   = "none";
}

function togglePass(inputId, btn) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  inp.type = inp.type === "password" ? "text" : "password";
  btn.style.opacity = inp.type === "text" ? "1" : ".5";
}

function _authSetLoading(form, on) {
  const btn  = document.getElementById(`${form}-btn`);
  const txt  = document.getElementById(`${form}-btn-txt`);
  const spin = document.getElementById(`${form}-spin`);
  if (btn)  btn.disabled = on;
  if (txt)  txt.style.display = on ? "none" : "inline";
  if (spin) spin.style.display = on ? "block" : "none";
}

function _authShowError(form, msg) {
  const el = document.getElementById(`${form}-error`);
  if (el) { el.textContent = msg; el.style.display = "block"; }
}

async function doLogin() {
  const user = document.getElementById("login-user")?.value.trim();
  const pass = document.getElementById("login-pass")?.value.trim();
  document.getElementById("login-error").style.display = "none";
  if (!user || !pass) { _authShowError("login","Enter username and password"); return; }

  _authSetLoading("login", true);
  try {
    const r = await fetch(`${API}/auth/login`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ username:user, password:pass }),
      credentials:"include"
    });
    const d = await r.json();
    if (!r.ok) { _authShowError("login", d.error || "Login failed"); return; }
    onAuthSuccess(d.user);
  } catch(e) {
    _authShowError("login","Network error — is the server running?");
  } finally {
    _authSetLoading("login", false);
  }
}

async function doRegister() {
  const name  = document.getElementById("reg-name")?.value.trim();
  const user  = document.getElementById("reg-user")?.value.trim();
  const email = document.getElementById("reg-email")?.value.trim();
  const pass  = document.getElementById("reg-pass")?.value.trim();
  document.getElementById("reg-error").style.display = "none";
  if (!name || !user || !email || !pass) { _authShowError("reg","All fields are required"); return; }

  _authSetLoading("reg", true);
  try {
    const r = await fetch(`${API}/auth/register`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ full_name:name, username:user, email, password:pass }),
      credentials:"include"
    });
    const d = await r.json();
    if (!r.ok) { _authShowError("reg", d.error || "Registration failed"); return; }
    onAuthSuccess(d.user);
    toast("🎉 Account created! Welcome to TeleBot");
  } catch(e) {
    _authShowError("reg","Network error — is the server running?");
  } finally {
    _authSetLoading("reg", false);
  }
}

async function doLogout() {
  try {
    await fetch(`${API}/auth/logout`, { method:"POST", credentials:"include" });
  } catch {}
  S.user = null;
  setUserWidget(null);
  showAuthModal();
  toast("👋 Signed out");
}

function onAuthSuccess(user) {
  S.user = user;
  hideAuthModal();
  setUserWidget(user);
  toast(`👋 Welcome, ${user.full_name || user.username}!`);
}

function setUserWidget(user) {
  const widget = document.getElementById("tb-user");
  if (!widget) return;
  if (!user) { widget.style.display = "none"; return; }
  widget.style.display = "flex";
  const av = document.getElementById("tb-avatar");
  const un = document.getElementById("tb-username");
  if (av) av.textContent = (user.avatar || user.full_name?.slice(0,2) || "?").toUpperCase();
  if (un) un.textContent = user.username || user.full_name;
}

async function checkSession() {
  try {
    const r = await fetch(`${API}/auth/me`, { credentials:"include" });
    if (r.ok) {
      const d = await r.json();
      if (d.id) { onAuthSuccess(d); return; }
    }
  } catch {}
  showAuthModal();
}

// Enter key support on auth forms
document.addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const ov = document.getElementById("auth-overlay");
  if (!ov || ov.style.display === "none") return;
  const loginVisible = document.getElementById("auth-login-form")?.style.display !== "none";
  if (loginVisible) doLogin(); else doRegister();
});

// ─── Navigation ──────────────────────────────────────────────
function nav(id, btn) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".sb-item").forEach(b => b.classList.remove("active"));
  document.getElementById("pg-" + id).classList.add("active");
  if (btn) btn.classList.add("active");
  const labels = { home:"Dashboard", payment:"Pay & Recharge", myplan:"My Plan",
    quiz:"AI Quiz", tutor:"AI Tutor", triage:"Support Triage", plans:"Plan Explorer", vdb:"Vector DB" };
  setText("tb-page", labels[id] || id);
  if (id === "plans")   renderPlans(PLANS);
  if (id === "payment") { loadTransactions(); }
  if (id === "triage")  { loadTriageStats(); loadTickets(); }
  document.querySelector(".sidebar")?.classList.remove("open");
}
// keep old navigate() alias so existing onclick calls still work
function navigate(id, btn) { nav(id, btn); }
function toggleSidebar() { document.querySelector(".sidebar")?.classList.toggle("open"); }

// ─── Health check ─────────────────────────────────────────────
async function checkHealth() {
  const pill = document.getElementById("llm-pill");
  const led  = document.getElementById("sys-led");
  const stxt = document.getElementById("sys-txt");
  const atxt = document.getElementById("ai-txt");
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(4000) });
    if (!r.ok) throw new Error("not ok");
    const d = await r.json();
    S.llmOn = d.llm_available !== false;
    if (pill) pill.className = "tb-chip " + (S.llmOn ? "on" : "off");
    if (atxt) atxt.textContent = S.llmOn ? "Gemini Online" : "Set API Key";
    if (led)  led.className = "status-dot " + (S.llmOn ? "on" : "off");
    if (stxt) stxt.textContent = S.llmOn ? "System Online" : "AI Key Missing";
    if (d.vectordb) {
      setText("vdb-plans",    d.vectordb.plans_indexed    ?? 8);
      setText("vdb-concepts", d.vectordb.concepts_indexed ?? 11);
      setText("vdb-metric",   d.vectordb.similarity_metric ?? "cosine");
    }
  } catch {
    if (pill) pill.className = "tb-chip";
    if (atxt) atxt.textContent = "Checking…";
    if (led)  led.className = "status-dot";
    if (stxt) stxt.textContent = "Connecting…";
  }
}

// ═══════════════════════════════════════════════════════════════
//  PAYMENT DASHBOARD
// ═══════════════════════════════════════════════════════════════
const SVC_CONFIG = {
  mobile:      { title:"Mobile Recharge",       numLabel:"Mobile Number",      numPH:"Enter 10-digit number",    showType:true,  detect:true  },
  dth:         { title:"DTH Recharge",          numLabel:"Subscriber ID",      numPH:"Enter DTH subscriber ID",  showType:false, detect:false },
  broadband:   { title:"Broadband Bill",        numLabel:"Account Number",     numPH:"Enter account number",     showType:false, detect:false },
  postpaid:    { title:"Postpaid Bill",         numLabel:"Mobile Number",      numPH:"Enter 10-digit number",    showType:false, detect:true  },
  electricity: { title:"Electricity Bill",      numLabel:"Consumer Number",    numPH:"Enter consumer number",    showType:false, detect:false },
  gas:         { title:"Gas Bill",              numLabel:"Customer ID",        numPH:"Enter customer ID",        showType:false, detect:false },
  water:       { title:"Water Bill",            numLabel:"Account Number",     numPH:"Enter account number",     showType:false, detect:false },
  landline:    { title:"Landline Bill",         numLabel:"Phone Number",       numPH:"Enter landline number",    showType:false, detect:false },
};

function selectService(svc, btnEl) {
  S.svc = svc; S.selectedOp = null; S.selectedPlan = null; S._allLoadedPlans = [];

  document.querySelectorAll(".svc-btn").forEach(b => b.classList.remove("active"));
  const tab = btnEl || document.querySelector(`[data-svc="${svc}"]`);
  if (tab) tab.classList.add("active");

  const cfg = SVC_CONFIG[svc] || SVC_CONFIG.mobile;
  setText("pay-title", cfg.title);
  setText("num-label", cfg.numLabel);

  const pn = document.getElementById("pay-number");
  if (pn) { pn.placeholder = cfg.numPH; pn.value = ""; }

  // Reset detected badge
  const badge = document.getElementById("op-badge");
  if (badge) badge.style.display = "none";
  const hint = document.getElementById("detect-hint");
  if (hint) hint.style.display = "none";

  // Plan type toggle
  const ptr = document.getElementById("plan-type-row");
  if (ptr) ptr.style.display = cfg.showType ? "flex" : "none";

  // Reset plan list
  const plw = document.getElementById("plan-list-wrap");
  if (plw) plw.innerHTML = `<div class="plan-empty-state"><div class="pes-ico">📋</div><div class="pes-txt">Select an operator to see plans</div></div>`;

  // Reset plan cats & search
  const pc = document.getElementById("plan-cats");
  if (pc) pc.style.display = "none";
  const psi = document.getElementById("plan-search-inp");
  if (psi) { psi.style.display = "none"; psi.value = ""; }

  // Reset summary
  const spb = document.getElementById("selected-plan-bar");
  if (spb) spb.style.display = "none";
  const pb  = document.getElementById("pay-btn");
  if (pb)  pb.disabled = true;

  loadOperators(svc);
}

async function loadOperators(svc) {
  const opGrp = document.getElementById("op-select-grp");
  const opGrid = document.getElementById("op-grid");
  if (!opGrp || !opGrid) return;
  opGrp.style.display = "block";

  // Always show operator chips — mobile auto-detects, others pick manually
  const fallback = {
    mobile:["Jio","Airtel","Vi","BSNL"],
    postpaid:["Jio","Airtel","Vi","BSNL"],
    dth:["Tata Play","Airtel DTH","Dish TV","Sun Direct","D2H"],
    broadband:["Jio Fiber","Airtel Xstream","BSNL Fiber","ACT Fibernet"],
    electricity:["BSES Rajdhani","BSES Yamuna","TPDDL","MSEDCL","BESCOM","TNEB","UPPCL"],
    gas:["Indraprastha Gas","Mahanagar Gas","Gujarat Gas","Adani Gas"],
    water:["Delhi Jal Board","MCGM","BWSSB","CMWSSB"],
    landline:["BSNL Landline","MTNL","Airtel Landline","JioFiber Landline"],
  };
  const logos = { Jio:"🟦", Airtel:"🔴", Vi:"🟣", BSNL:"🟡" };

  try {
    const r = await fetch(`${API}/payment/operators?service=${svc}`);
    const d = await r.json();
    const ops = d.operators || [];
    if (!ops.length) throw new Error("empty");
    opGrid.innerHTML = ops.map(op =>
      `<div class="op-chip" onclick="selectOperator('${op.id||op.name}','${op.name||op.id}','${op.logo||"📡"}',this)">
        <span class="op-chip-ico">${op.logo || "📡"}</span>
        <span>${op.name || op.id}</span>
      </div>`).join("");
  } catch {
    const list = fallback[svc] || [];
    opGrid.innerHTML = list.map(name =>
      `<div class="op-chip" onclick="selectOperator('${name}','${name}','${logos[name]||"📡"}',this)">
        <span class="op-chip-ico">${logos[name]||"📡"}</span>
        <span>${name}</span>
      </div>`).join("");
  }
}

async function selectOperator(opId, opName, opLogo, el) {
  S.selectedOp = opId; S.selectedPlan = null;
  document.querySelectorAll(".op-chip").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");

  // Show detected badge on mobile
  if (S.svc === "mobile" || S.svc === "postpaid") {
    const badge = document.getElementById("op-badge");
    const logo  = document.getElementById("op-badge-logo");
    const name  = document.getElementById("op-badge-name");
    if (badge) badge.style.display = "flex";
    if (logo)  logo.textContent = opLogo;
    if (name)  name.textContent = opName;
  }
  await loadPlans(opId, S.planType);
}

async function loadPlans(opId, planType) {
  const wrap = document.getElementById("plan-list-wrap");
  if (!wrap) return;
  wrap.innerHTML = `<div class="plan-empty-state"><div class="pes-ico">⏳</div><div class="pes-txt">Loading plans…</div></div>`;
  S.selectedPlan = null;
  const spb = document.getElementById("selected-plan-bar");
  if (spb) spb.style.display = "none";
  const pb = document.getElementById("pay-btn");
  if (pb) pb.disabled = true;

  let plans = [];
  try {
    const r = await fetch(`${API}/payment/plans?operator=${opId}&type=${planType}&service=${S.svc}`);
    const d = await r.json();
    plans = d.plans || [];
  } catch {
    const opData = OP_PLANS[opId];
    if (opData) plans = planType === "postpaid" ? opData.postpaid : opData.prepaid;
  }

  S._allLoadedPlans = plans;

  // Show search & category filters
  const pc  = document.getElementById("plan-cats");
  const psi = document.getElementById("plan-search-inp");
  if (!plans.length) {
    wrap.innerHTML = `<div class="plan-empty-state"><div class="pes-ico">📭</div><div class="pes-txt">No plans found</div></div>`;
    if (pc)  pc.style.display  = "none";
    if (psi) psi.style.display = "none";
    return;
  }
  if (pc)  { pc.style.display = "flex"; document.querySelectorAll(".pc").forEach(b => b.classList.remove("active")); pc.firstElementChild?.classList.add("active"); }
  if (psi) psi.style.display = "block";

  renderPlanRows(plans);
}

function renderPlanRows(plans) {
  const wrap = document.getElementById("plan-list-wrap");
  if (!wrap) return;
  if (!plans.length) {
    wrap.innerHTML = `<div class="plan-empty-state"><div class="pes-ico">🔍</div><div class="pes-txt">No plans match</div></div>`;
    return;
  }
  wrap.innerHTML = plans.map(p => {
    const extras = (p.extras || p.features || []).slice(0, 2).join(" · ");
    const badge = p.category === "popular" ? `<span class="pr-badge pop">🔥 Popular</span>` :
                  p.category === "5g"      ? `<span class="pr-badge g5">⚡ 5G</span>` :
                  p.category === "budget"  ? `<span class="pr-badge bud">💰 Budget</span>` : "";
    return `
      <div class="plan-row" onclick="selectPlan(${JSON.stringify(p).replace(/"/g,'&quot;')},this)">
        <div class="pr-price"><div class="pr-amt">₹${p.price}</div><div class="pr-gst">+GST</div></div>
        <div class="pr-info">
          <div class="pr-name">${p.name || `₹${p.price} Plan`}</div>
          <div class="pr-meta">${p.validity||""} · ${p.data||p.speed||""} · ${p.calls||""}</div>
          ${extras ? `<div class="pr-extra">✓ ${extras}</div>` : ""}
        </div>
        <div class="pr-right">${badge}<span class="pr-val">${p.validity||""}</span></div>
      </div>`;
  }).join("");
}

function filterPayByCat(cat, btn) {
  document.querySelectorAll(".pc").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  const filtered = cat === "all" ? S._allLoadedPlans : S._allLoadedPlans.filter(p => p.category === cat);
  renderPlanRows(filtered);
}

function filterPlanListPayment(q) {
  if (!q.trim()) { renderPlanRows(S._allLoadedPlans); return; }
  const lq = q.toLowerCase();
  renderPlanRows(S._allLoadedPlans.filter(p =>
    [p.name, p.data, p.validity, p.calls, ...(p.extras||[])].some(v => (v||"").toLowerCase().includes(lq))
  ));
}

function selectPlan(plan, el) {
  S.selectedPlan = plan;
  document.querySelectorAll(".plan-row").forEach(i => i.classList.remove("selected"));
  el.classList.add("selected");

  const spb = document.getElementById("selected-plan-bar");
  if (spb) spb.style.display = "flex";
  setText("spb-name",  plan.name || `₹${plan.price} Plan`);
  setText("spb-meta",  `${plan.validity||""} · ${plan.data||plan.speed||""}`);
  setText("spb-price", `₹${plan.price}`);

  const pb = document.getElementById("pay-btn");
  if (pb) { pb.disabled = false; pb.textContent = `Pay ₹${plan.price}`; }
}

function setPlanType(type, btn) {
  S.planType = type;
  document.querySelectorAll(".toggle-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  if (S.selectedOp) loadPlans(S.selectedOp, type);
}

// Auto-detect operator from number input
let _dt = null;
function onNumberInput(val) {
  const digits = val.replace(/\D/g, "");
  if ((S.svc !== "mobile" && S.svc !== "postpaid") || digits.length < 10) return;
  clearTimeout(_dt);
  _dt = setTimeout(async () => {
    const hint = document.getElementById("detect-hint");
    const msg  = document.getElementById("detect-msg");
    if (hint) hint.style.display = "block";
    if (msg)  msg.textContent = "🔍 Detecting operator…";
    try {
      const r = await fetch(`${API}/payment/detect`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ mobile: digits })
      });
      const d = await r.json();
      if (d.detected) {
        if (msg) msg.textContent = `✅ ${d.operator} detected`;
        document.querySelectorAll(".op-chip").forEach(chip => {
          if (chip.textContent.trim().includes(d.operator)) chip.click();
        });
      } else {
        if (msg) msg.textContent = "❓ Select operator manually";
      }
    } catch {
      const op = detectOperatorLocal(digits);
      if (msg) msg.textContent = `✅ ${op} detected`;
      document.querySelectorAll(".op-chip").forEach(chip => {
        if (chip.textContent.trim().includes(op)) chip.click();
      });
    }
  }, 600);
}

async function proceedPayment() {
  const number = document.getElementById("pay-number")?.value.trim();
  if (!number) { toast("⚠️ Enter a number first"); return; }
  if (!S.selectedPlan) { toast("⚠️ Select a plan first"); return; }

  const btn = document.getElementById("pay-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Processing…"; }

  try {
    const r = await fetch(`${API}/payment/recharge`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ service:S.svc, operator:S.selectedOp, number, plan_id:S.selectedPlan?.id||"", amount:S.selectedPlan?.price||0 })
    });
    const d = await r.json();
    if (d.success) { showPayModal(d); loadTransactions(); }
    else toast("❌ " + (d.error || "Payment failed"));
  } catch {
    showPayModal({ transaction_id:`TXN${Math.floor(Math.random()*90000000+10000000)}`, operator:S.selectedOp||"Unknown", number, amount:S.selectedPlan?.price||0, plan:S.selectedPlan?.name||"Recharge" });
    loadTransactions();
  }

  if (btn) { btn.disabled = false; btn.textContent = `Pay ₹${S.selectedPlan?.price||""}`; }
}

function showPayModal(d) {
  document.getElementById("modal-txn").textContent = `TXN ID: ${d.transaction_id}`;
  document.getElementById("modal-detail").innerHTML =
    `<strong>${d.operator}</strong> · ${d.number}<br>Plan: ${d.plan||`₹${d.amount}`}<br>Amount: <strong style="color:var(--va)">₹${d.amount}</strong>`;
  document.getElementById("pay-modal").style.display = "flex";
}
function closePayModal() { document.getElementById("pay-modal").style.display = "none"; }

async function loadTransactions() {
  const list = document.getElementById("txn-list");
  if (!list) return;
  list.innerHTML = `<div class="txn-loading">Loading…</div>`;
  try {
    const r = await fetch(`${API}/payment/transactions`);
    const d = await r.json();
    const txns = d.transactions || [];
    if (!txns.length) { list.innerHTML = `<div class="txn-loading">No transactions yet</div>`; return; }
    const icos = { Mobile:"📱", DTH:"📺", Broadband:"🌐", Electricity:"⚡", Gas:"🔥", Water:"💧", Landline:"☎️" };
    list.innerHTML = txns.map(t => `
      <div class="txn-item">
        <div class="ti-ico">${icos[t.service]||"💳"}</div>
        <div class="ti-info">
          <div class="ti-op">${t.operator}</div>
          <div class="ti-num">${t.number} · ${t.plan}</div>
        </div>
        <div class="ti-right">
          <div class="ti-amt">₹${t.amount}</div>
          <span class="ti-status ${(t.status||"").toLowerCase()}">${t.status}</span>
        </div>
      </div>`).join("");
  } catch {
    list.innerHTML = `<div class="txn-loading">Error loading</div>`;
  }
}

// ═══════════════════════════════════════════════════════════════
//  MY PLAN
// ═══════════════════════════════════════════════════════════════
async function detectMyPlan() {
  const num = document.getElementById("myplan-number")?.value.trim().replace(/\D/g,"");
  if (!num || num.length < 10) { toast("⚠️ Enter a valid 10-digit number"); return; }

  const btn = document.getElementById("myplan-btn");
  if (btn) { btn.disabled = true; btn.innerHTML = "Checking…"; }

  try {
    const r = await fetch(`${API}/payment/my-plan`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ mobile: num })
    });
    const d = await r.json();
    if (d.error) { toast("❌ " + d.error); }
    else showMyPlan(d);
  } catch {
    const op     = detectOperatorLocal(num);
    const opData = OP_PLANS[op] || OP_PLANS["Jio"];
    const all    = [...opData.prepaid, ...opData.postpaid];
    const mid    = Math.floor(opData.prepaid.length / 2);
    const cur    = opData.prepaid[mid] || all[0];
    showMyPlan({ mobile:num, operator:op, logo:opData.logo, color:opData.color,
      current_plan:cur, alternatives:all.filter(p=>p.id!==cur.id).sort((a,b)=>a.price-b.price) });
  }

  if (btn) { btn.disabled = false; btn.innerHTML = `Check Plans <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`; }
}

function detectOperatorLocal(num) {
  const d = num.replace(/\D/g,"").slice(-10);
  const p2 = d.substring(0,2);
  if (["62","63","64","65","70","71","72","73","74","75","76","77","78","79"].includes(p2)) return "Jio";
  if (["80","81","82","83","84","85","86","87","88","89"].includes(p2)) return "Airtel";
  if (["90","91","92","93"].includes(p2)) return "Vi";
  if (d.startsWith("9436")||d.startsWith("9415")||d.startsWith("9450")) return "BSNL";
  const p3 = d.substring(0,3);
  if (["987","988","989","991","992","993","994","995","800","801","982","983","984","985","986"].includes(p3)) return "Airtel";
  if (["900","901","902","903","904","905","906","907","908","909","910","911","912","913","914","915","916","917","918","919","920"].includes(p3)) return "Vi";
  return "Jio";
}

function showMyPlan(d) {
  S.myPlanOp = d.operator;
  S.currentPlan = d.current_plan;
  S.allAltPlans = d.alternatives || [];

  // Operator banner
  setText("op-banner-logo", d.logo || "📱");
  setText("op-banner-name", d.operator);
  const raw = d.mobile || "";
  setText("op-banner-num", raw.length === 10 ? `+91 ${raw.slice(0,5)} ${raw.slice(5)}` : raw);

  // Current plan card
  const cur = d.current_plan;
  const extras = (cur.extras || []).map(e => `<span class="cpc-extra">${e}</span>`).join("");
  const validDays = parseInt(cur.validity) || 28;
  const daysLeft  = Math.floor(validDays * 0.71);
  document.getElementById("current-plan-card").innerHTML = `
    <div class="cur-plan-card">
      <div class="cpc-price">₹${cur.price}</div>
      <div class="cpc-name">${cur.name}</div>
      <div class="cpc-specs">
        <div><div class="cpc-spec-lbl">Data</div><div class="cpc-spec-val">${cur.data||"—"}</div></div>
        <div><div class="cpc-spec-lbl">Calls</div><div class="cpc-spec-val">${cur.calls||"—"}</div></div>
        <div><div class="cpc-spec-lbl">SMS</div><div class="cpc-spec-val">${cur.sms||"—"}</div></div>
        <div><div class="cpc-spec-lbl">Validity</div><div class="cpc-spec-val">${cur.validity||"—"}</div></div>
      </div>
      ${extras ? `<div class="cpc-extras">${extras}</div>` : ""}
      <button class="cpc-renew-btn" onclick="goRechargeFromPlan()">🔄 Renew at ₹${cur.price}</button>
    </div>`;

  // Usage bars
  setText("data-total",  cur.data || "—");
  setText("days-left", `${daysLeft} days left`);
  const validPct = Math.round((daysLeft / validDays) * 100);
  const vf = document.getElementById("valid-fill");
  if (vf) vf.style.width = `${validPct}%`;

  // Show result, hide empty
  document.getElementById("myplan-result").style.display = "block";
  const emp = document.getElementById("myplan-empty");
  if (emp) emp.style.display = "none";

  // Render alternatives
  filterAltPlans("all", document.querySelector(".pf-btn"));
  setTimeout(() => document.getElementById("myplan-result").scrollIntoView({ behavior:"smooth", block:"start" }), 100);
}

function filterAltPlans(cat, btn) {
  document.querySelectorAll(".pf-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  const plans = cat === "all" ? S.allAltPlans : S.allAltPlans.filter(p => p.category === cat);
  renderAltPlans(plans);
}

function renderAltPlans(plans) {
  const grid = document.getElementById("alt-plans-grid");
  if (!grid) return;
  if (!plans.length) {
    grid.innerHTML = `<div style="color:var(--txt3);padding:20px;font-size:13px;grid-column:1/-1">No plans in this category</div>`;
    return;
  }
  grid.innerHTML = plans.map(p => {
    const extras   = (p.extras||[]).slice(0,3).map(e=>`<span class="ac-extra">${e}</span>`).join("");
    const cat      = p.category || "";
    const badgeCls = cat === "5g" ? "ac-badge-5g" : `ac-badge ${cat}`;
    const badgeTxt = { popular:"🔥 Popular", budget:"💰 Budget", "5g":"⚡ 5G", annual:"🗓️ Annual", long:"📅 Long", postpaid:"💳 Postpaid" }[cat] || "";
    return `
      <div class="alt-card">
        <div class="ac-top">
          <div class="ac-price">₹${p.price}<span>/recharge</span></div>
          ${badgeTxt ? `<span class="${badgeCls}">${badgeTxt}</span>` : ""}
        </div>
        <div class="ac-name">${p.name}</div>
        <div class="ac-specs">
          <div><div class="ac-sl">Data</div><div class="ac-sv">${p.data||"—"}</div></div>
          <div><div class="ac-sl">Validity</div><div class="ac-sv">${p.validity||"—"}</div></div>
          <div><div class="ac-sl">Calls</div><div class="ac-sv">${p.calls||"—"}</div></div>
          <div><div class="ac-sl">SMS</div><div class="ac-sv">${p.sms||"—"}</div></div>
        </div>
        ${extras ? `<div class="ac-extras">${extras}</div>` : ""}
        <button class="ac-btn" onclick="rechargePlan(${JSON.stringify(p).replace(/"/g,'&quot;')})">
          Recharge ₹${p.price} →
        </button>
      </div>`;
  }).join("");
}

function rechargePlan(plan) {
  const num = document.getElementById("myplan-number")?.value.trim();
  nav("payment", document.getElementById("nb-payment"));
  setTimeout(() => {
    selectService("mobile", document.querySelector('[data-svc="mobile"]'));
    const ni = document.getElementById("pay-number");
    if (ni && num) { ni.value = num; onNumberInput(num); }
    setTimeout(() => {
      document.querySelectorAll(".op-chip").forEach(chip => {
        if (chip.textContent.trim().includes(S.myPlanOp||"")) chip.click();
      });
      setTimeout(() => {
        document.querySelectorAll(".plan-row").forEach(row => {
          const amt = row.querySelector(".pr-amt");
          if (amt?.textContent === `₹${plan.price}`) row.click();
        });
      }, 700);
    }, 500);
  }, 200);
}

function goRechargeFromPlan() {
  const num = document.getElementById("myplan-number")?.value.trim();
  nav("payment", document.getElementById("nb-payment"));
  setTimeout(() => {
    const ni = document.getElementById("pay-number");
    if (ni && num) { ni.value = num; onNumberInput(num); }
  }, 300);
}

function resetMyPlan() {
  document.getElementById("myplan-result").style.display = "none";
  const emp = document.getElementById("myplan-empty");
  if (emp) emp.style.display = "block";
  const mn = document.getElementById("myplan-number");
  if (mn) mn.value = "";
  S.myPlanOp = null; S.currentPlan = null; S.allAltPlans = [];
}

function previewOperator(op) {
  const opData = OP_PLANS[op];
  if (!opData) return;
  const inp = document.getElementById("myplan-number");
  const nums = { Jio:"7012345678", Airtel:"9876543210", Vi:"9212345678", BSNL:"9436123456" };
  if (inp) inp.value = nums[op] || "9876543210";
  showMyPlan({
    mobile: inp?.value || "Demo", operator:op, logo:opData.logo, color:opData.color,
    current_plan: opData.prepaid[Math.floor(opData.prepaid.length/2)] || opData.prepaid[0],
    alternatives: [...opData.prepaid.slice(0,2), ...opData.prepaid.slice(3), ...opData.postpaid],
  });
}

// ═══════════════════════════════════════════════════════════════
//  AI QUIZ
// ═══════════════════════════════════════════════════════════════
function setDiff(d, btn) {
  S.diff = d;
  document.querySelectorAll(".diff-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

async function startQuiz() {
  hide("quiz-start"); show("quiz-active"); hide("score-screen");
  S.qi=0; S.qc=0; S.qw=0; S.sessionId=null; S.aiGenerated=false;

  const qcard = document.getElementById("q-card");
  if (qcard) { qcard.style.opacity="0.5"; }
  const qt = document.getElementById("q-txt");
  if (qt) qt.textContent = "⏳ Generating AI questions…";
  const opts = document.getElementById("options");
  if (opts) opts.innerHTML = "";

  try {
    const r = await fetch(`${API}/quiz/questions?difficulty=${S.diff}&count=8`);
    const d = await r.json();
    S.qqs         = d.questions;
    S.sessionId   = d.session_id || null;
    S.aiGenerated = d.ai_generated || false;
    const badge   = document.getElementById("ai-gen-badge");
    if (badge) badge.style.display = S.aiGenerated ? "inline-flex" : "none";
    if (S.aiGenerated) toast("✨ Fresh AI questions generated!");
  } catch {
    S.qqs = shuffle(QUESTIONS.filter(q => S.diff === "all" || q.difficulty === S.diff)).slice(0,8);
  }

  if (qcard) qcard.style.opacity = "1";
  renderQ();
}

function renderQ() {
  const q = S.qqs[S.qi], tot = S.qqs.length;
  setText("q-prog-lbl", `Q ${S.qi+1} / ${tot}`);
  setText("qpr-score", `${S.score} pts`);
  setText("q-score-lbl", `${S.score} pts`);
  const pf = document.getElementById("prog-fill");
  if (pf) pf.style.width = `${(S.qi/tot)*100}%`;
  setText("q-idx", `Q${String(S.qi+1).padStart(2,"0")}`);

  const db = document.getElementById("q-diff-b");
  if (db) { db.textContent = (q.difficulty||"medium").toUpperCase(); db.className = `qc-diff ${q.difficulty||"medium"}`; }
  setText("q-topic-b", q.topic || "Telecom");
  setText("q-txt", q.question);

  const opts = document.getElementById("options");
  if (opts) opts.innerHTML = Object.entries(q.options).map(([k,v]) =>
    `<button class="opt" onclick="pick('${k}','${q.id}',this)">
      <span class="opt-k">${k}</span>
      <span class="opt-t">${v}</span>
      <span class="opt-r"></span>
    </button>`).join("");

  hide("exp-card"); hide("next-btn");
  const card = document.getElementById("q-card");
  if (card) {
    card.style.opacity="0"; card.style.transform="translateY(8px)";
    requestAnimationFrame(() => {
      card.style.transition="opacity .28s ease, transform .28s ease";
      card.style.opacity="1"; card.style.transform="translateY(0)";
    });
  }
}

async function pick(ans, qid, el) {
  document.querySelectorAll(".opt").forEach(b => b.disabled = true);
  const exp  = document.getElementById("exp-card");
  const exph = document.getElementById("exp-head");
  const expb = document.getElementById("exp-body");
  if (exp) exp.style.display = "block";
  if (exph) { exph.className = "ec-header th"; exph.textContent = "✦ AI Explanation"; }
  if (expb) expb.innerHTML = `<div class="thinking"><span>Analyzing with Gemini + RAG</span><div class="td"></div><div class="td"></div><div class="td"></div></div>`;

  let ok=false, ck="", expl="";
  try {
    const body = { question_id:qid, answer:ans };
    if (S.sessionId) body.session_id = S.sessionId;
    const r = await fetch(`${API}/quiz/submit`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    ok = d.is_correct; ck = d.correct_key||d.correct_answer; expl = d.explanation;
  } catch {
    const qd = QUESTIONS.find(q => q.id === qid);
    if (qd) {
      ok = ans === qd.correct; ck = qd.correct;
      expl = ok ? `**✅ Correct!** The answer is **${qd.options[qd.correct]}**.\n\n**💡 Tip:** Great job!`
                : `**❌ Not quite.** Correct: **${qd.options[qd.correct]}**.\n\n**💡 Keep going!**`;
    }
  }

  if (ok) {
    S.qc++; S.score += 10;
    setText("q-score-lbl", `${S.score} pts`);
    setText("tb-score", S.score);
    setText("sb-score", S.score);
    const sv = document.getElementById("sb-score");
    if (sv) { sv.style.transform="scale(1.3)"; setTimeout(()=>{sv.style.transform="scale(1)";},280); }
    toast("✨ +10 points!");
  } else { S.qw++; }

  document.querySelectorAll(".opt").forEach(b => {
    const k  = b.querySelector(".opt-k")?.textContent;
    const ri = b.querySelector(".opt-r");
    if (k === ck)              { b.classList.add("correct"); if(ri) ri.textContent="✓"; }
    else if (k===ans && !ok)   { b.classList.add("wrong");   if(ri) ri.textContent="✗"; }
  });

  if (exph) {
    exph.className = "ec-header " + (ok ? "c" : "w");
    exph.innerHTML = ok
      ? `<svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/></svg> Correct!`
      : `<svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/></svg> Here's what to know`;
  }
  if (expb) expb.innerHTML = bold(expl).replace(/\n/g,"<br>");
  show("next-btn");
  setTimeout(() => document.getElementById("exp-card")?.scrollIntoView({ behavior:"smooth", block:"nearest" }), 100);
}

function nextQ() {
  S.qi++;
  if (S.qi >= S.qqs.length) showScore();
  else renderQ();
}

function showScore() {
  hide("quiz-active"); show("score-screen");
  const tot = S.qqs.length, pct = Math.round((S.qc/tot)*100);
  setText("sc-emoji",   pct>=90?"🏆":pct>=70?"🎯":pct>=50?"📡":"💪");
  setText("sc-title",   pct>=90?"Outstanding!":pct>=70?"Well Done!":pct>=50?"Good Progress!":"Keep Practicing!");
  setText("sc-pct",     pct+"%");
  setText("sc-sub",     `${S.qc} correct out of ${tot}`);
  setText("sc-correct", S.qc);
  setText("sc-wrong",   S.qw);
  setText("sc-pts",     S.score);
}
function resetQuiz() { hide("score-screen"); show("quiz-start-card")||show("quiz-start"); hide("quiz-active"); }

// ═══════════════════════════════════════════════════════════════
//  AI TUTOR
// ═══════════════════════════════════════════════════════════════
function sendSug(el) {
  const ta = document.getElementById("chat-ta");
  if (ta) ta.value = el.textContent;
  const sr = document.getElementById("sug-row");
  if (sr) sr.style.display = "none";
  sendMsg();
}

async function sendMsg() {
  const ta  = document.getElementById("chat-ta");
  const msg = ta?.value.trim();
  if (!msg) return;
  if (ta) { ta.value = ""; ta.style.height = "auto"; }
  addMsg(msg, "user");
  const sb = document.getElementById("send-btn");
  if (sb) sb.disabled = true;
  const tid = "t" + Date.now();
  addThinking(tid);

  try {
    const r = await fetch(`${API}/quiz/chat`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ message:msg, history:S.history })
    });
    const d = await r.json();
    removeEl(tid);
    const reply = d.reply || d.response || "No response";
    addMsg(reply, "bot");
    S.history.push({ role:"user", content:msg }, { role:"assistant", content:reply });
    if (S.history.length > 20) S.history = S.history.slice(-20);
  } catch {
    removeEl(tid);
    addMsg(localPlanAnswer(msg), "bot");
  }
  if (sb) sb.disabled = false;
}

function localPlanAnswer(msg) {
  const m = msg.toLowerCase();
  for (const [op, data] of Object.entries(OP_PLANS)) {
    if (m.includes(op.toLowerCase())) {
      const list = data.prepaid.slice(0,5).map(p => `• **${p.name}** — ₹${p.price} | ${p.validity} | ${p.data} | ${p.calls} calls`).join("\n");
      return `Here are **${op} Prepaid Plans**:\n\n${list}\n\n💡 Use **My Plan** page to enter your number and recharge directly!`;
    }
  }
  return "⚠️ Backend offline. Check your API key and server status.";
}

function addMsg(txt, type) {
  const box = document.getElementById("chat-box");
  if (!box) return;
  const d = document.createElement("div");
  const isBot = type === "bot";
  const now   = new Date().toLocaleTimeString([], { hour:"2-digit", minute:"2-digit" });
  d.className = `chat-msg ${type}`;
  d.innerHTML = `
    <div class="cm-avatar ${isBot?"bot-av":"user-av"}">${isBot?"📡":"You"}</div>
    <div class="cm-content">
      <div class="cm-bubble ${isBot?"bot-bubble":"user-bubble"}">${bold(txt).replace(/\n/g,"<br>")}</div>
      <div class="cm-time">${now}</div>
    </div>`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function addThinking(id) {
  const box = document.getElementById("chat-box");
  if (!box) return;
  const d = document.createElement("div");
  d.id = id; d.className = "chat-msg bot";
  d.innerHTML = `<div class="cm-avatar bot-av">📡</div><div class="cm-content"><div class="cm-bubble bot-bubble"><div class="thinking"><span>Thinking</span><div class="td"></div><div class="td"></div><div class="td"></div></div></div></div>`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}
function removeEl(id) { document.getElementById(id)?.remove(); }

// ═══════════════════════════════════════════════════════════════
//  PLAN EXPLORER
// ═══════════════════════════════════════════════════════════════
function renderPlans(plans) {
  const g = document.getElementById("plans-grid");
  if (!plans?.length) { g.innerHTML = `<p style="color:var(--txt3);padding:20px">No plans found.</p>`; return; }
  g.innerHTML = plans.map(p => {
    const t  = (p.type||"").toLowerCase();
    const bc = t.includes("iot")?"iot":t.includes("international")?"int":t.includes("enterprise")?"ent":t.includes("postpaid")?"pos":"pre";
    const pr = (p.price||"—").replace("INR","₹").replace("/month","/mo");
    const fs = (p.features||[]).slice(0,4).map(f=>`<span class="plan-f">${f.trim()}</span>`).join("");
    return `<div class="plan-c">
      <div class="plan-top"><div class="plan-nm">${p.name}</div><span class="pb ${bc}">${(p.type||"PLAN").toUpperCase()}</span></div>
      <div class="plan-price">${pr}</div>
      <div class="plan-sg">
        <div><div class="plan-sl">Data</div><div class="plan-sv">${p.data||"—"}</div></div>
        <div><div class="plan-sl">Speed</div><div class="plan-sv">${p.speed||"—"}</div></div>
        <div><div class="plan-sl">Calls</div><div class="plan-sv">${p.calls||"—"}</div></div>
        <div><div class="plan-sl">Validity</div><div class="plan-sv">${p.validity||"—"}</div></div>
      </div>
      <div class="plan-fs">${fs}</div>
    </div>`;
  }).join("");
}

function filterPlans(q) {
  if (!q.trim()) { renderPlans(PLANS); return; }
  const lq = q.toLowerCase();
  renderPlans(PLANS.filter(p =>
    [p.name,p.type,p.best_for,p.data,p.speed,p.description,...(p.features||[])].some(v=>(v||"").toLowerCase().includes(lq))
  ));
}

// ═══════════════════════════════════════════════════════════════
//  UTILS
// ═══════════════════════════════════════════════════════════════
function toast(msg) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.querySelector("#toast-msg").textContent = msg;
  t.classList.add("show");
  clearTimeout(t._tid);
  t._tid = setTimeout(() => t.classList.remove("show"), 2800);
}
function setText(id, v) { const e = document.getElementById(id); if (e) e.textContent = v; }
function show(id)  { const e = document.getElementById(id); if (e) e.style.display = ""; }
function hide(id)  { const e = document.getElementById(id); if (e) e.style.display = "none"; }
function shuffle(a){ return [...a].sort(() => Math.random() - .5); }
function bold(t)   { return (t||"").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); }

// ═══════════════════════════════════════════════════════════════
//  LOCAL DATA — Fallback when API offline
// ═══════════════════════════════════════════════════════════════
const OP_PLANS = {
  "Jio":{ logo:"🟦", color:"#0070BA",
    prepaid:[
      {id:"jio_1",name:"Jio Basic",      price:155, validity:"24 days",data:"1.5GB/day",  calls:"Unlimited",sms:"100/day",category:"budget", extras:["JioTV","JioCinema"]},
      {id:"jio_2",name:"Jio Daily 2GB",  price:209, validity:"28 days",data:"2GB/day",   calls:"Unlimited",sms:"100/day",category:"popular",extras:["JioTV","JioCinema","JioCloud"]},
      {id:"jio_3",name:"Jio 3GB/day",    price:299, validity:"28 days",data:"3GB/day",   calls:"Unlimited",sms:"100/day",category:"popular",extras:["JioTV","JioCinema","Netflix Mobile"]},
      {id:"jio_4",name:"Jio 5G Boost",   price:349, validity:"28 days",data:"Unlimited 5G",calls:"Unlimited",sms:"100/day",category:"5g",   extras:["5G Unlimited","JioTV","JioCinema"]},
      {id:"jio_5",name:"Jio 84 Day",     price:533, validity:"84 days",data:"2GB/day",   calls:"Unlimited",sms:"100/day",category:"long",  extras:["JioTV","JioCinema"]},
      {id:"jio_6",name:"Jio Dhan Dhana", price:601, validity:"84 days",data:"3GB/day",   calls:"Unlimited",sms:"100/day",category:"long",  extras:["JioTV","JioCinema","Netflix Mobile"]},
      {id:"jio_7",name:"Jio Annual",     price:2999,validity:"365 days",data:"2.5GB/day",calls:"Unlimited",sms:"100/day",category:"annual",extras:["JioTV","JioCinema","JioCloud 100GB"]},
    ],
    postpaid:[
      {id:"jio_p1",name:"JioPostpaid 399",price:399,validity:"30 days",data:"75GB",     calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Netflix Mobile","Amazon Prime"]},
      {id:"jio_p2",name:"JioPostpaid 599",price:599,validity:"30 days",data:"125GB",    calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Netflix Basic","Amazon Prime","Disney+Hotstar"]},
      {id:"jio_p3",name:"JioPostpaid 999",price:999,validity:"30 days",data:"Unlimited",calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Netflix Standard","Amazon Prime","Disney+Hotstar"]},
    ]},
  "Airtel":{ logo:"🔴", color:"#ED1C24",
    prepaid:[
      {id:"air_1",name:"Airtel Budget",  price:99,  validity:"28 days",data:"1GB",          calls:"100 min",  sms:"300",    category:"budget", extras:["Wynk Music"]},
      {id:"air_2",name:"Airtel Smart",   price:179, validity:"28 days",data:"1.5GB/day",    calls:"Unlimited",sms:"100/day",category:"popular",extras:["Wynk Music","Airtel Thanks"]},
      {id:"air_3",name:"Airtel 2GB/day", price:239, validity:"28 days",data:"2GB/day",      calls:"Unlimited",sms:"100/day",category:"popular",extras:["Wynk Music","Apollo 24|7"]},
      {id:"air_4",name:"Airtel 3GB/day", price:329, validity:"28 days",data:"3GB/day",      calls:"Unlimited",sms:"100/day",category:"popular",extras:["Wynk Music","Amazon Prime 30d"]},
      {id:"air_5",name:"Airtel 5G Ultra",price:409, validity:"28 days",data:"Unlimited 5G", calls:"Unlimited",sms:"100/day",category:"5g",     extras:["5G Unlimited","Amazon Prime","Airtel Xstream"]},
      {id:"air_6",name:"Airtel 84 Day",  price:569, validity:"84 days",data:"2GB/day",      calls:"Unlimited",sms:"100/day",category:"long",   extras:["Wynk Music"]},
      {id:"air_7",name:"Airtel Annual",  price:3359,validity:"365 days",data:"2.5GB/day",   calls:"Unlimited",sms:"100/day",category:"annual", extras:["Wynk Music","Amazon Prime"]},
    ],
    postpaid:[
      {id:"air_p1",name:"Airtel Postpaid 399",price:399,validity:"30 days",data:"75GB",     calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Amazon Prime","Disney+Hotstar Mobile"]},
      {id:"air_p2",name:"Airtel Postpaid 499",price:499,validity:"30 days",data:"Unlimited",calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Amazon Prime","Netflix Mobile","Disney+Hotstar"]},
      {id:"air_p3",name:"Airtel Postpaid 999",price:999,validity:"30 days",data:"Unlimited",calls:"Unlimited+Intl",sms:"100/day",category:"postpaid",extras:["Netflix Basic","Amazon Prime","Disney+Hotstar","Intl Roaming"]},
    ]},
  "Vi":{ logo:"🟣", color:"#721D6B",
    prepaid:[
      {id:"vi_1",name:"Vi Budget",        price:99,  validity:"28 days",data:"1GB",         calls:"100 min",  sms:"300",    category:"budget", extras:["Vi Movies & TV"]},
      {id:"vi_2",name:"Vi Hero Unlimited",price:179, validity:"28 days",data:"1.5GB/day",   calls:"Unlimited",sms:"100/day",category:"popular",extras:["Vi Movies & TV","Weekend Rollover"]},
      {id:"vi_3",name:"Vi 2GB/day",       price:239, validity:"28 days",data:"2GB/day",     calls:"Unlimited",sms:"100/day",category:"popular",extras:["Vi Movies & TV","Binge All Night"]},
      {id:"vi_4",name:"Vi Hero 3GB",      price:299, validity:"28 days",data:"3GB/day",     calls:"Unlimited",sms:"100/day",category:"popular",extras:["Vi Movies & TV","Disney+Hotstar 30d"]},
      {id:"vi_5",name:"Vi 5G Ready",      price:359, validity:"28 days",data:"2.5GB/day",   calls:"Unlimited",sms:"100/day",category:"5g",     extras:["Vi Movies & TV","5G Ready"]},
      {id:"vi_6",name:"Vi 84 Day",        price:553, validity:"84 days",data:"1.5GB/day",   calls:"Unlimited",sms:"100/day",category:"long",   extras:["Vi Movies & TV"]},
      {id:"vi_7",name:"Vi Annual",        price:2899,validity:"365 days",data:"1.5GB/day",  calls:"Unlimited",sms:"100/day",category:"annual", extras:["Vi Movies & TV","Binge All Night"]},
    ],
    postpaid:[
      {id:"vi_p1",name:"Vi Red 399",price:399,validity:"30 days",data:"75GB",     calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Vi Movies & TV","Amazon Prime"]},
      {id:"vi_p2",name:"Vi Red 499",price:499,validity:"30 days",data:"100GB",    calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Vi Movies & TV","Amazon Prime","Netflix Mobile"]},
      {id:"vi_p3",name:"Vi Red 699",price:699,validity:"30 days",data:"Unlimited",calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Vi Movies & TV","Amazon Prime","Netflix Basic","Disney+Hotstar"]},
    ]},
  "BSNL":{ logo:"🟡", color:"#F7A600",
    prepaid:[
      {id:"bsnl_1",name:"BSNL STV 94", price:94,  validity:"28 days", data:"2GB/day",calls:"Unlimited",sms:"100/day",category:"budget", extras:["Zing Music"]},
      {id:"bsnl_2",name:"BSNL STV 197",price:197, validity:"54 days", data:"2GB/day",calls:"Unlimited",sms:"100/day",category:"popular",extras:["Zing Music"]},
      {id:"bsnl_3",name:"BSNL STV 247",price:247, validity:"30 days", data:"3GB/day",calls:"Unlimited",sms:"100/day",category:"popular",extras:["Zing Music"]},
      {id:"bsnl_4",name:"BSNL 81 Day", price:398, validity:"81 days", data:"3GB/day",calls:"Unlimited",sms:"100/day",category:"long",   extras:["Zing Music"]},
      {id:"bsnl_5",name:"BSNL Annual", price:1515,validity:"365 days",data:"2GB/day",calls:"Unlimited",sms:"100/day",category:"annual", extras:["Zing Music"]},
    ],
    postpaid:[
      {id:"bsnl_p1",name:"BSNL Plan 99", price:99, validity:"30 days",data:"2GB",     calls:"250 min",  sms:"100",    category:"postpaid",extras:[]},
      {id:"bsnl_p2",name:"BSNL Plan 349",price:349,validity:"30 days",data:"Unlimited",calls:"Unlimited",sms:"100/day",category:"postpaid",extras:["Zing Music"]},
    ]},
};

const PLANS = [
  {name:"BasicConnect 4G",  type:"Prepaid",             price:"₹199/month",  data:"1GB",          speed:"25 Mbps",   calls:"100 min",      validity:"28 days", features:["No contract","Data rollover","Auto-renewal"],          best_for:"Light users"},
  {name:"SmartDaily 5G",    type:"Prepaid",             price:"₹299/month",  data:"2GB/day",      speed:"5G 1 Gbps", calls:"Unlimited",     validity:"28 days", features:["5G ready","Netflix basic","Wi-Fi calling"],            best_for:"Streaming"},
  {name:"FamilyShare Pro",  type:"Postpaid",            price:"₹999/month",  data:"100GB shared", speed:"500 Mbps",  calls:"Unlimited",     validity:"30 days", features:["4 members","Disney+ Hotstar","Intl roaming 20 countries"],best_for:"Families"},
  {name:"BusinessElite 5G", type:"Postpaid Enterprise", price:"₹1499/month", data:"Unlimited",    speed:"2 Gbps",    calls:"Unlim+500 intl",validity:"30 days", features:["Static IP","VPN","Microsoft 365","SLA 99.9%","IoT Portal"],best_for:"Enterprise"},
  {name:"TravelGlobal SIM", type:"International",       price:"₹2499/month", data:"5GB intl",     speed:"150 Mbps",  calls:"200 intl min",  validity:"30 days", features:["150+ countries","No roaming charges","Lounge 2x/month"], best_for:"Travelers"},
  {name:"IoTConnect M2M",   type:"IoT / M2M",           price:"₹49/SIM/mo",  data:"500MB",        speed:"NB-IoT/LTE-M",calls:"N/A",         validity:"30 days", features:["NB-IoT","LTE-M","Bulk SIM API","FOTA updates"],        best_for:"Smart devices"},
  {name:"StudentFlex",      type:"Prepaid",             price:"₹149/56 days",data:"1.5GB/day",    speed:"150 Mbps",  calls:"Unlimited",     validity:"56 days", features:["Education zero-rating","Google One 15GB","Night unlimited"],best_for:"Students"},
  {name:"StreamMax 5G",     type:"Postpaid",            price:"₹699/month",  data:"75GB",         speed:"1.5 Gbps",  calls:"Unlimited",     validity:"30 days", features:["4K UHD optimized","Netflix+Prime+Hotstar+SonyLIV+Zee5","Binge-On"],best_for:"Entertainment"},
];

const QUESTIONS = [
  {id:"q001",question:"Which telecom plan is specifically designed for IoT and M2M communication?",options:{A:"SmartDaily 5G",B:"IoTConnect M2M",C:"BusinessElite 5G",D:"BasicConnect 4G"},correct:"B",topic:"IoT Plans",difficulty:"easy"},
  {id:"q002",question:"The FamilyShare Pro plan allows data sharing among how many members?",options:{A:"2 members",B:"3 members",C:"4 members",D:"6 members"},correct:"C",topic:"Family Plans",difficulty:"easy"},
  {id:"q003",question:"Which plan offers a Static IP address for hosting servers and VPNs?",options:{A:"FamilyShare Pro",B:"StreamMax 5G",C:"BusinessElite 5G",D:"TravelGlobal SIM"},correct:"C",topic:"Business Plans",difficulty:"medium"},
  {id:"q004",question:"What maximum data speed does BusinessElite 5G deliver on priority network?",options:{A:"150 Mbps",B:"500 Mbps",C:"1 Gbps",D:"2 Gbps"},correct:"D",topic:"Network Speeds",difficulty:"medium"},
  {id:"q005",question:"StudentFlex zero-rates which category of applications?",options:{A:"Gaming apps",B:"Social media",C:"Education apps",D:"Entertainment apps"},correct:"C",topic:"Special Plans",difficulty:"easy"},
  {id:"q006",question:"Which two low-power protocols does IoTConnect M2M support?",options:{A:"3G and 4G LTE",B:"NB-IoT and LTE-M",C:"WiFi 6 and Bluetooth 5",D:"LoRa and Zigbee"},correct:"B",topic:"IoT Protocols",difficulty:"hard"},
  {id:"q007",question:"TravelGlobal SIM provides international coverage in how many countries?",options:{A:"50+",B:"75+",C:"100+",D:"150+"},correct:"D",topic:"International Plans",difficulty:"easy"},
  {id:"q008",question:"Which plan includes Microsoft 365 Basic as a bundled enterprise benefit?",options:{A:"StudentFlex",B:"FamilyShare Pro",C:"BusinessElite 5G",D:"SmartDaily 5G"},correct:"C",topic:"Plan Benefits",difficulty:"medium"},
];

// ═══════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
//  TRIAGE AGENT — Problem Statement 3
// ═══════════════════════════════════════════════════════════════

const TRIAGE_SAMPLES = [
  // 0 — Network Outage (CRITICAL)
  `My mobile internet has been completely down since last night. I cannot make or receive calls either. This is extremely urgent as I run a business from my phone and I'm losing clients. My mobile number is 9876543210, account ID CA654321. The network tower near Koramangala seems down. Please fix this IMMEDIATELY.`,
  // 1 — Billing Dispute (HIGH)
  `I have been charged ₹599 twice for my Airtel postpaid plan in the month of March. My account number is ACC789012 and my number is 9811234567. I checked my bank statement and there are two debits of ₹599 on 5th March and again on 12th March. I want a full refund of the duplicate charge. This is unacceptable.`,
  // 2 — Roaming Issue (HIGH)
  `I am currently traveling in Dubai and my Jio SIM is not working for calls or data. I had specifically activated the Jio international roaming pack for ₹2499 before leaving India on 15th April. My number is 7012345678. I have an important business meeting tomorrow and need this resolved urgently.`,
  // 3 — Plan Query (LOW)
  `Hi, I want to know which plan is best for my family. We have 4 members and all use smartphones for streaming and calls. Our current Airtel plan gives 1.5GB per day but it's not enough. What plans do you have that offer more data and also include Netflix or Hotstar? Budget is around ₹1000 per month.`,
  // 4 — Complaint (MEDIUM)
  `I am extremely disappointed with the customer service I received when I called your helpline yesterday. The agent was very rude and kept me on hold for 45 minutes without resolving my issue. My complaint is about slow internet speeds for the past two weeks. My BSNL plan ID is bsnl_3 and mobile is 9436123456. I want this escalated to a senior manager.`,
];

let _triageChannel  = "chat";
let _currentTicket  = null;
let _allTickets     = [];
let _queueFilter    = "all";

function setChannel(ch, btn) {
  _triageChannel = ch;
  document.querySelectorAll(".ch-tab").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

function loadSample(idx) {
  const ta = document.getElementById("triage-input");
  if (ta) { ta.value = TRIAGE_SAMPLES[idx]; ta.focus(); }
}

async function runTriage() {
  const msg = document.getElementById("triage-input")?.value.trim();
  if (!msg) { toast("⚠️ Please enter a customer message"); return; }
  if (msg.length < 10) { toast("⚠️ Message is too short to analyze"); return; }

  const btn = document.getElementById("triage-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Analyzing…"; }

  // Show loading state
  const placeholder = document.getElementById("triage-placeholder");
  const body        = document.getElementById("triage-result-body");
  if (placeholder) placeholder.style.display = "flex";
  if (body) body.style.display = "none";

  try {
    const r = await fetch(`${API}/triage/analyze`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, channel: _triageChannel })
    });
    const d = await r.json();

    if (d.error) { toast("❌ " + d.error); return; }

    _currentTicket = d;
    renderTriageResult(d);
    renderNER(d.entities);
    loadTickets();
    loadTriageStats();
    toast(`✅ Ticket ${d.ticket_id} created`);

  } catch (e) {
    // Demo fallback
    const fallback = buildDemoResult(msg);
    _currentTicket = fallback;
    renderTriageResult(fallback);
    renderNER(fallback.entities);
    _allTickets.unshift(fallback);
    renderTicketList(_allTickets);
    toast("✅ Ticket created (offline mode)");
  }

  if (btn) { btn.disabled = false; btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Analyze &amp; Triage`; }
}

function buildDemoResult(msg) {
  // Client-side triage for offline demo
  const m = msg.toLowerCase();
  let urgency = "MEDIUM", intent = "general";
  if (/emergency|urgent|critical|not working|no service|down|outage/.test(m)) urgency = "HIGH";
  if (/hospital|life|fire|ambulance|completely dead/.test(m)) urgency = "CRITICAL";
  if (/plan|upgrade|info|inquiry|question/.test(m)) urgency = "LOW";
  if (/bill|charge|refund|amount|overcharged/.test(m)) intent = "billing";
  else if (/outage|no service|not working|network down/.test(m)) intent = "outage";
  else if (/roaming|international|abroad/.test(m)) intent = "roaming";
  else if (/slow|speed|buffering/.test(m)) intent = "speed";
  else if (/complaint|rude|disappointed/.test(m)) intent = "complaint";
  else if (/plan|upgrade|data|recharge/.test(m)) intent = "plan_change";

  const phones  = (msg.match(/[6-9]\d{9}/g) || []);
  const amounts = (msg.match(/(?:₹|Rs\.?)\s*(\d+)/g) || []);
  const accs    = (msg.match(/(?:CA|ACC|CUST)\s*\d+/gi) || []);

  const intMap = { billing:"Billing Issue", outage:"Service Outage", roaming:"Roaming Issue", speed:"Speed Issue", complaint:"General Complaint", plan_change:"Plan Change", general:"General Inquiry" };

  return {
    ticket_id: `TKT-${new Date().toISOString().slice(0,10).replace(/-/g,"")}-${Math.random().toString(36).slice(2,8).toUpperCase()}`,
    urgency, intent, intent_label: intMap[intent]||"General Inquiry",
    urgency_reason: `Detected ${urgency.toLowerCase()} priority signals`,
    confidence: 0.75,
    sentiment: urgency === "CRITICAL" || urgency === "HIGH" ? "frustrated" : "neutral",
    key_issues: [intMap[intent]||"General Issue"],
    entities: { phone_numbers: phones, account_ids: accs.map(a => a.replace(/\s/g,"")), amounts: amounts.map(a => a.replace(/[₹Rs\.]/g,"").trim()), dates: [], operators: ["Jio","Airtel","Vi","BSNL"].filter(o => msg.toLowerCase().includes(o.toLowerCase())), plan_names: [], ticket_refs: [] },
    draft_response: `Dear Customer,\n\nThank you for reaching out to TeleBot Support. We sincerely apologize for the inconvenience you are experiencing.\n\nWe have registered your concern and created ticket ${"{ticket_id}"}. Our team will review your case with high priority.\n\nTo assist you better, please confirm your registered mobile number and account ID. We will get back to you within 2-4 hours.\n\nWarm regards,\nTeleBot Support Team`,
    resolution_steps: ["Verify customer identity and account", "Review account history", "Identify root cause", "Apply fix or escalate", "Confirm resolution with customer"],
    handle_time: urgency === "CRITICAL" ? "2-5 minutes" : urgency === "HIGH" ? "5-15 minutes" : "15-30 minutes",
    escalate: urgency === "CRITICAL" || intent === "outage",
    escalation_reason: urgency === "CRITICAL" ? "Critical issue requiring immediate specialist" : "",
    ai_powered: false, status: "OPEN",
    created_at: new Date().toISOString(), channel: _triageChannel, processing_ms: 12,
  };
}

function renderTriageResult(d) {
  const ph   = document.getElementById("triage-placeholder");
  const body = document.getElementById("triage-result-body");
  if (ph)   ph.style.display   = "none";
  if (body) body.style.display = "block";

  // Header
  const hdr = document.getElementById("tr-header");
  if (hdr) hdr.className = `tr-header ${d.urgency}`;
  setText("tr-urgency-label", d.urgency);
  setText("tr-urgency-reason", d.urgency_reason || "");
  const ib = document.getElementById("tr-intent-badge");
  if (ib) ib.textContent = d.intent_label || d.intent;
  setText("tr-confidence", `${Math.round((d.confidence || 0.75) * 100)}% confidence`);
  const aib = document.getElementById("tr-ai-badge");
  if (aib) aib.style.display = d.ai_powered ? "block" : "none";

  // Ticket bar
  setText("tr-ticket-id", d.ticket_id || "");
  setText("tr-channel", `via ${(d.channel || "chat").toUpperCase()}`);
  setText("tr-handle-time", d.handle_time || "—");

  // Sentiment + escalation
  const sent = document.getElementById("tr-sentiment");
  if (sent) sent.textContent = `😤 Customer feeling: ${(d.sentiment || "neutral").charAt(0).toUpperCase() + (d.sentiment||"neutral").slice(1)}`;
  const esc = document.getElementById("tr-escalate");
  if (esc) { esc.style.display = d.escalate ? "block" : "none"; if (d.escalate && d.escalation_reason) esc.textContent = `⚠️ ${d.escalation_reason}`; }

  // Key issues
  const issues = document.getElementById("tr-issues");
  if (issues) issues.innerHTML = (d.key_issues || []).map(i => `<span class="tr-issue-tag">${i}</span>`).join("") || `<span class="tr-issue-tag">${d.intent_label}</span>`;

  // Draft response
  const draft = document.getElementById("tr-draft");
  if (draft) draft.textContent = (d.draft_response || "").replace("{ticket_id}", d.ticket_id || "");

  // Resolution steps
  const steps = document.getElementById("tr-steps");
  if (steps) steps.innerHTML = (d.resolution_steps || []).map((s, i) =>
    `<div class="tr-step"><div class="tr-step-num">${i+1}</div><div class="tr-step-txt">${s}</div></div>`
  ).join("");
}

function renderNER(entities) {
  if (!entities) return;
  const card = document.getElementById("ner-card");
  const grid = document.getElementById("ner-grid");
  if (!card || !grid) return;

  const hasAny = Object.values(entities).some(v => Array.isArray(v) && v.length > 0);
  card.style.display = hasAny ? "block" : "none";
  if (!hasAny) return;

  const rows = [
    { key: "phone_numbers", label: "Phone Numbers", cls: "phone" },
    { key: "account_ids",   label: "Account IDs",   cls: "" },
    { key: "amounts",       label: "Amounts",        cls: "amount" },
    { key: "operators",     label: "Operators",      cls: "op" },
    { key: "dates",         label: "Dates",          cls: "" },
    { key: "plan_names",    label: "Plans",          cls: "" },
    { key: "ticket_refs",   label: "References",     cls: "" },
  ];

  grid.innerHTML = rows.filter(r => entities[r.key]?.length)
    .map(r => `
      <div class="ner-row">
        <div class="ner-type">${r.label}</div>
        <div class="ner-values">
          ${entities[r.key].map(v => `<span class="ner-tag ${r.cls}">${v}</span>`).join("")}
        </div>
      </div>`).join("") || `<div class="ner-empty">No entities detected</div>`;
}

function copyDraft() {
  const draft = document.getElementById("tr-draft")?.textContent || "";
  navigator.clipboard?.writeText(draft).then(() => toast("📋 Draft copied!")).catch(() => toast("Copy failed"));
}

async function updateStatus(status) {
  if (!_currentTicket) { toast("⚠️ No active ticket"); return; }
  try {
    const r = await fetch(`${API}/triage/tickets/${_currentTicket.ticket_id}/status`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    const d = await r.json();
    if (d.ticket_id) { _currentTicket = d; toast(`✅ Status updated to ${status}`); loadTickets(); }
  } catch {
    // Offline update
    if (_currentTicket) { _currentTicket.status = status; toast(`✅ Status: ${status}`); renderTicketList(_allTickets); }
  }
}

// Ticket queue
async function loadTickets() {
  try {
    const r = await fetch(`${API}/triage/tickets?limit=30`);
    const d = await r.json();
    _allTickets = d.tickets || [];
    renderTicketList(_allTickets);
  } catch {
    renderTicketList(_allTickets); // use in-memory
  }
}

function filterQueue(f, btn) {
  _queueFilter = f;
  document.querySelectorAll(".qf").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderTicketList(_allTickets);
}

function renderTicketList(tickets) {
  const list = document.getElementById("ticket-list");
  if (!list) return;

  let filtered = tickets;
  if (_queueFilter === "CRITICAL") filtered = tickets.filter(t => t.urgency === "CRITICAL");
  else if (_queueFilter === "HIGH") filtered = tickets.filter(t => t.urgency === "HIGH");
  else if (_queueFilter === "OPEN") filtered = tickets.filter(t => t.status === "OPEN");

  if (!filtered.length) {
    list.innerHTML = `<div class="tl-empty">No tickets${_queueFilter !== "all" ? " matching filter" : " yet"}</div>`;
    return;
  }

  list.innerHTML = filtered.map(t => `
    <div class="ticket-card ${t.urgency}" onclick="viewTicket('${t.ticket_id}')">
      <div class="tc-top">
        <span class="tc-id">${t.ticket_id}</span>
        <span class="tc-urg ${t.urgency}">${t.urgency}</span>
      </div>
      <div class="tc-intent">${t.intent_label || t.intent}</div>
      <div class="tc-preview">${(t.original_message || "").substring(0, 60)}…</div>
      <span class="tc-status ${t.status}">${t.status.replace("_"," ")}</span>
    </div>`).join("");
}

async function viewTicket(ticketId) {
  let ticket = _allTickets.find(t => t.ticket_id === ticketId);
  if (!ticket) {
    try {
      const r = await fetch(`${API}/triage/tickets/${ticketId}`);
      ticket = await r.json();
    } catch { return; }
  }
  _currentTicket = ticket;
  renderTriageResult(ticket);
  renderNER(ticket.entities);
  // Fill input with original message
  const ta = document.getElementById("triage-input");
  if (ta && ticket.original_message) ta.value = ticket.original_message;
}

// Stats
async function loadTriageStats() {
  try {
    const r = await fetch(`${API}/triage/stats`);
    const d = await r.json();
    setText("ts-total",    d.total || 0);
    setText("ts-critical", d.by_urgency?.CRITICAL || 0);
    setText("ts-high",     d.by_urgency?.HIGH     || 0);
    setText("ts-medium",   d.by_urgency?.MEDIUM   || 0);
    setText("ts-low",      d.by_urgency?.LOW      || 0);
    setText("ts-ai",       d.ai_powered || 0);
    setText("ts-esc",      d.escalations || 0);
  } catch {
    // Offline stats from in-memory
    const tickets = _allTickets;
    setText("ts-total",    tickets.length);
    setText("ts-critical", tickets.filter(t => t.urgency === "CRITICAL").length);
    setText("ts-high",     tickets.filter(t => t.urgency === "HIGH").length);
    setText("ts-medium",   tickets.filter(t => t.urgency === "MEDIUM").length);
    setText("ts-low",      tickets.filter(t => t.urgency === "LOW").length);
    setText("ts-ai",       tickets.filter(t => t.ai_powered).length);
    setText("ts-esc",      tickets.filter(t => t.escalate).length);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkSession();   // ← checks existing session; shows auth modal if not logged in
  checkHealth();
  renderPlans(PLANS);
  selectService("mobile", document.querySelector('[data-svc="mobile"]'));

  // Chat textarea auto-resize + enter-to-send
  const ta = document.getElementById("chat-ta");
  if (ta) {
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 120) + "px"; });
    ta.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMsg(); } });
  }

  // My plan enter key
  const mn = document.getElementById("myplan-number");
  if (mn) mn.addEventListener("keydown", e => { if (e.key === "Enter") detectMyPlan(); });

  // Pay number input
  const pn = document.getElementById("pay-number");
  if (pn) pn.addEventListener("input", e => onNumberInput(e.target.value));

  // Health poll
  setInterval(checkHealth, 30000);

  // Mobile responsive sidebar
  const mb = document.getElementById("menu-btn");
  const checkMobile = () => { if (mb) mb.style.display = window.innerWidth < 700 ? "flex" : "none"; };
  checkMobile();
  window.addEventListener("resize", checkMobile);

  // Click outside sidebar to close
  document.addEventListener("click", e => {
    const sb = document.querySelector(".sidebar");
    if (sb?.classList.contains("open") && !sb.contains(e.target) && !e.target.closest("#menu-btn")) {
      sb.classList.remove("open");
    }
  });
});