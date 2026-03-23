// ════════════════════════════════════════════
// TELECOMM INTELLIGENCE PLATFORM
// Complete frontend JS — auth, dashboard,
// plans, bills, calls, quiz bot, AI tutor
// ════════════════════════════════════════════

'use strict';

// ── State ─────────────────────────────────
let currentUser   = null;
let chatHistory   = [];

// Quiz state
let quizQuestions  = [];
let quizIndex      = 0;
let quizScore      = 0;
let quizCorrect    = 0;
let quizWrong      = 0;
let quizStreak     = 0;
let quizBestStreak = 0;
let quizTopicMap   = {};
let quizDiff       = 'all';
let quizTimer      = null;
let quizTimeLeft   = 30;

// ── Init ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
  loadPreviewPlans();
});

// ════════════════════════════════════════════
//  AUTHENTICATION
// ════════════════════════════════════════════

async function checkAuth() {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'include' });
    if (res.ok) {
      currentUser = await res.json();
      showApp();
      loadDashboard();
      loadQuizStats();
    } else {
      showPublic();
    }
  } catch {
    showPublic();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login_username').value.trim();
  const password = document.getElementById('login_password').value.trim();
  const btn      = document.getElementById('loginBtn');

  hideError('loginError');
  if (!username || !password) { showError('loginError', 'Please enter username and password'); return; }

  setLoading(btn, 'Logging in...');
  try {
    const res  = await fetch('/api/auth/login', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
      currentUser = data.user;
      document.getElementById('loginForm').reset();
      showToast('Welcome back, ' + currentUser.full_name + '!', 'success');
      showApp();
      loadDashboard();
      loadQuizStats();
    } else {
      showError('loginError', data.error || 'Invalid credentials');
    }
  } catch {
    showError('loginError', 'Connection error. Please try again.');
  }
  resetLoading(btn, '<i class="fas fa-sign-in-alt"></i> Login');
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById('reg_fullname').value.trim();
  const username  = document.getElementById('reg_username').value.trim();
  const email     = document.getElementById('reg_email').value.trim();
  const password  = document.getElementById('reg_password').value.trim();
  const btn       = document.getElementById('registerBtn');

  hideError('registerError');
  if (!full_name || !username || !email || !password) { showError('registerError', 'All fields are required'); return; }
  if (username.length < 3) { showError('registerError', 'Username must be at least 3 characters'); return; }
  if (!email.includes('@')) { showError('registerError', 'Enter a valid email address'); return; }
  if (password.length < 6)  { showError('registerError', 'Password must be at least 6 characters'); return; }

  setLoading(btn, 'Creating account...');
  try {
    const res  = await fetch('/api/auth/register', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, username, email, password })
    });
    const data = await res.json();
    if (res.ok) {
      currentUser = data.user;
      document.getElementById('registerForm').reset();
      showToast('Account created! Welcome ' + currentUser.full_name + '!', 'success');
      showApp();
      loadDashboard();
      loadQuizStats();
    } else {
      showError('registerError', data.error || 'Registration failed');
    }
  } catch {
    showError('registerError', 'Connection error. Please try again.');
  }
  resetLoading(btn, '<i class="fas fa-user-plus"></i> Create Account');
}

async function handleLogout() {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  currentUser = null;
  chatHistory = [];
  clearInterval(quizTimer);
  showPublic();
  showToast('Logged out successfully', 'success');
}

// ════════════════════════════════════════════
//  APP VISIBILITY
// ════════════════════════════════════════════

function showPublic() {
  document.getElementById('navbar').style.display         = 'none';
  document.getElementById('main-container').style.display = 'none';
  document.getElementById('footer').style.display         = 'none';
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('landing-page').classList.add('active');
}

function showApp() {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('navbar').style.display         = 'block';
  document.getElementById('main-container').style.display = 'block';
  document.getElementById('footer').style.display         = 'block';
  document.getElementById('dashboard-page').classList.add('active');

  if (currentUser) {
    const av = (currentUser.full_name || 'U').substring(0, 2).toUpperCase();
    document.getElementById('userAvatar').textContent  = av;
    document.getElementById('menuName').textContent    = currentUser.full_name;
    document.getElementById('menuEmail').textContent   = currentUser.email;
    document.getElementById('welcomeMsg').textContent  = 'Welcome back, ' + currentUser.full_name + '!';
  }
}

// ════════════════════════════════════════════
//  NAVIGATION
// ════════════════════════════════════════════

function switchPage(page) {
  // Public-only pages
  if (['landing', 'login', 'register'].includes(page)) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById(page + '-page');
    if (el) el.classList.add('active');
    return;
  }

  // Protected — require login
  if (!currentUser) {
    showToast('Please login to access this feature', 'error');
    switchPage('login');
    return;
  }

  document.querySelectorAll('#main-container .page').forEach(p => p.classList.remove('active'));
  const el = document.getElementById(page + '-page');
  if (el) el.classList.add('active');

  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  window.scrollTo(0, 0);
  toggleMenu(true); // close dropdown

  if (page === 'dashboard')     loadDashboard();
  if (page === 'plans')         loadPlans();
  if (page === 'bills')         loadBills();
  if (page === 'calls')         loadCalls();
  if (page === 'profile')       loadProfile();
  if (page === 'quiz-history')  loadQuizHistory();
  if (page === 'notifications') loadNotifications();
}

// ════════════════════════════════════════════
//  LANDING — preview plans (public)
// ════════════════════════════════════════════

async function loadPreviewPlans() {
  try {
    const plans = await fetch('/api/plans').then(r => r.json());
    document.getElementById('previewPlans').innerHTML = plans.map(p => `
      <div class="preview-plan-card ${p.popular ? 'popular' : ''}">
        ${p.popular ? '<div class="plan-badge">⭐ Popular</div>' : ''}
        <h3>₹${p.price}<small>/mo</small></h3>
        <p>${p.name}</p>
        <ul>${p.features.slice(0,3).map(f => `<li>✓ ${f}</li>`).join('')}</ul>
        <button class="btn btn-outline-primary btn-sm btn-full" onclick="switchPage('register')">Get Started</button>
      </div>`).join('');
  } catch(e) { console.error(e); }
}

// ════════════════════════════════════════════
//  DASHBOARD
// ════════════════════════════════════════════

async function loadDashboard() {
  try {
    const [plan, bill, usage, calls] = await Promise.all([
      apiFetch('/api/plan'),
      apiFetch('/api/bill'),
      apiFetch('/api/usage'),
      apiFetch('/api/calls?limit=5'),
    ]);
    if (!plan) return;

    setText('planName',  plan.name);
    setText('planPrice', '₹' + plan.price);
    setText('calls',     plan.calls);
    setText('sms',       plan.sms);
    setText('data',      plan.data);
    setText('billAmount', '₹' + bill.amount);
    setText('billPeriod', bill.period);

    setBar('callsBar', 'callsPct', usage.calls_percent);
    setBar('smsBar',   'smsPct',   usage.sms_percent);
    setBar('dataBar',  'dataPct',  usage.data_percent);

    document.getElementById('callsList').innerHTML = (calls || []).map(callHTML).join('') ||
      '<p style="color:var(--gray);text-align:center;padding:20px;">No recent calls</p>';
  } catch(e) { console.error('Dashboard error:', e); }
}

function callHTML(c) {
  return `<div class="call-item">
    <div class="call-icon ${c.type}">${c.type === 'incoming' ? '📥' : '📤'}</div>
    <div class="call-info"><h4>${c.name}</h4><p>${new Date(c.date).toLocaleString()}</p></div>
    <div class="call-details">
      <span>${Math.floor(c.duration / 60)}m ${c.duration % 60}s</span>
      <span class="call-cost">₹${c.cost.toFixed(2)}</span>
    </div>
  </div>`;
}

// ════════════════════════════════════════════
//  PLANS
// ════════════════════════════════════════════

async function loadPlans() {
  try {
    const [plans, myPlan] = await Promise.all([
      fetch('/api/plans').then(r => r.json()),
      apiFetch('/api/plan'),
    ]);
    document.getElementById('plansGrid').innerHTML = plans.map(p => `
      <div class="card plan-card ${p.popular ? 'popular' : ''} ${myPlan && p.id === myPlan.id ? 'current-plan' : ''}">
        ${p.popular ? '<div class="plan-badge">⭐ Popular</div>' : ''}
        ${myPlan && p.id === myPlan.id ? '<div class="current-badge">✓ Your Plan</div>' : ''}
        <h3 class="plan-name">${p.name}</h3>
        <p class="plan-price">₹${p.price}<small>/month</small></p>
        <ul class="plan-features">${p.features.map(f => `<li>${f}</li>`).join('')}</ul>
        <button class="btn ${myPlan && p.id === myPlan.id ? 'btn-outline-primary' : 'btn-primary'} btn-full"
          onclick="selectPlan(${p.id}, '${p.name}')"
          ${myPlan && p.id === myPlan.id ? 'disabled' : ''}>
          ${myPlan && p.id === myPlan.id ? 'Current Plan' : 'Select Plan'}
        </button>
      </div>`).join('');
  } catch(e) { console.error(e); }
}

async function selectPlan(id, name) {
  if (!confirm(`Switch to ${name}?`)) return;
  try {
    const res = await fetch('/api/plan/change', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: id })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Plan changed to ' + name + '!', 'success');
      loadPlans();
    }
  } catch(e) { showToast('Error changing plan', 'error'); }
}

// ════════════════════════════════════════════
//  BILLS
// ════════════════════════════════════════════

async function loadBills() {
  try {
    const bill = await apiFetch('/api/bill');
    document.getElementById('billsContainer').innerHTML = `
      <div class="bill-item">
        <div class="bill-info">
          <h4>${bill.period}</h4>
          <p>Base: ₹${bill.breakdown.base} + Tax (18%): ₹${bill.breakdown.tax}</p>
          <p><strong>Total: ₹${bill.amount}</strong></p>
          <p>Status: <span class="badge ${bill.status === 'pending' ? 'badge-warning' : 'badge-success'}">${bill.status.toUpperCase()}</span></p>
          <p style="font-size:12px;color:var(--gray);margin-top:4px;">Due: ${bill.due_date}</p>
        </div>
        <div class="bill-actions">
          <button class="btn btn-primary" onclick="payBill()">Pay Now</button>
        </div>
      </div>`;
  } catch(e) { console.error(e); }
}

async function payBill() {
  if (!confirm('Proceed with payment?')) return;
  try {
    const res  = await fetch('/api/bill/pay', { method: 'POST', credentials: 'include' });
    const data = await res.json();
    showToast('Payment successful! Ref: ' + data.transaction_id, 'success');
    setTimeout(loadBills, 1000);
  } catch(e) { showToast('Payment failed. Try again.', 'error'); }
}

// ════════════════════════════════════════════
//  CALLS
// ════════════════════════════════════════════

async function loadCalls() {
  try {
    const calls = await apiFetch('/api/calls');
    document.getElementById('callsFullList').innerHTML = (calls || []).map(callHTML).join('') ||
      '<p style="color:var(--gray);text-align:center;padding:20px;">No call history found</p>';
  } catch(e) { console.error(e); }
}

// ════════════════════════════════════════════
//  PROFILE
// ════════════════════════════════════════════

async function loadProfile() {
  try {
    const [user, plan] = await Promise.all([
      apiFetch('/api/user/profile'),
      apiFetch('/api/plan'),
    ]);
    if (!user) return;
    document.getElementById('profileAvatar').textContent   = (user.full_name || 'U').substring(0,2).toUpperCase();
    document.getElementById('profileName').textContent     = user.full_name;
    document.getElementById('profileUsername').textContent = '@' + user.username;
    document.getElementById('prof_fullname').value = user.full_name || '';
    document.getElementById('prof_email').value    = user.email || '';
    document.getElementById('prof_phone').value    = user.phone || '';
    document.getElementById('memberSince').textContent = user.member_since || '—';
    document.getElementById('profilePlan').textContent = plan ? plan.name + ' — ₹' + plan.price + '/mo' : '—';
  } catch(e) { console.error(e); }
}

async function updateProfile(e) {
  e.preventDefault();
  const data = {
    full_name: document.getElementById('prof_fullname').value.trim(),
    email:     document.getElementById('prof_email').value.trim(),
    phone:     document.getElementById('prof_phone').value.trim(),
  };
  if (!data.full_name || !data.email) { showToast('Name and email are required', 'error'); return; }
  try {
    const res = await fetch('/api/user/profile', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();
    if (result.success) {
      currentUser = result.user;
      showToast('Profile updated!', 'success');
    }
  } catch(e) { showToast('Update failed', 'error'); }
}

// ════════════════════════════════════════════
//  NOTIFICATIONS
// ════════════════════════════════════════════

async function loadNotifications() {
  try {
    const notifs = await apiFetch('/api/notifications');
    document.getElementById('notifContainer').innerHTML =
      `<h3 style="margin-bottom:14px;"><i class="fas fa-bell"></i> Notifications</h3>` +
      (notifs || []).map(n => `
        <div class="notif-item ${n.read ? '' : 'unread'}">
          <i class="fas ${n.type === 'alert' ? 'fa-exclamation-circle' : n.type === 'offer' ? 'fa-tag' : 'fa-credit-card'}"></i>
          <div><p>${n.message}</p><small>${n.date}</small></div>
        </div>`).join('');
    const unread = (notifs || []).filter(n => !n.read).length;
    document.getElementById('notifDot').style.display = unread > 0 ? 'block' : 'none';
  } catch(e) { console.error(e); }
}

// ════════════════════════════════════════════
//  QUIZ BOT
// ════════════════════════════════════════════

function setDiff(btn) {
  document.querySelectorAll('.diff-pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  quizDiff = btn.dataset.val;
}

async function startQuiz() {
  const count = document.getElementById('quizCount').value;
  try {
    const res = await fetch(`/api/quiz/questions?difficulty=${quizDiff}&count=${count}`, { credentials: 'include' });
    if (res.status === 401) { showToast('Please login to take the quiz', 'error'); return; }
    quizQuestions  = await res.json();
    quizIndex      = 0;
    quizScore      = 0;
    quizCorrect    = 0;
    quizWrong      = 0;
    quizStreak     = 0;
    quizBestStreak = 0;
    quizTopicMap   = {};

    document.getElementById('quizSetup').style.display  = 'none';
    document.getElementById('quizActive').style.display = 'block';
    document.getElementById('quizResult').style.display = 'none';
    showQuestion();
  } catch(e) { showToast('Error loading questions', 'error'); }
}

function showQuestion() {
  if (quizIndex >= quizQuestions.length) { showQuizResult(); return; }

  clearInterval(quizTimer);
  quizTimeLeft = 30;

  const q     = quizQuestions[quizIndex];
  const total = quizQuestions.length;
  const pct   = Math.round((quizIndex / total) * 100);

  // Topbar
  document.getElementById('qTopicPill').textContent  = q.topic;
  const diffEl = document.getElementById('qDiffPill');
  diffEl.textContent = q.difficulty;
  diffEl.className   = `diff-badge ${q.difficulty}`;
  document.getElementById('qCurrent').textContent    = quizIndex + 1;
  document.getElementById('qTotal').textContent      = total;
  document.getElementById('quizProgBar').style.width = pct + '%';

  // Live score
  document.getElementById('liveScore').textContent   = quizScore;
  document.getElementById('liveCorrect').textContent = quizCorrect;
  document.getElementById('liveWrong').textContent   = quizWrong;

  // Streak
  const streakEl = document.getElementById('streakCounter');
  if (quizStreak >= 2) {
    streakEl.style.display = 'flex';
    document.getElementById('streakNum').textContent = quizStreak + '🔥';
  } else {
    streakEl.style.display = 'none';
  }

  // Question & options
  document.getElementById('quizQuestion').textContent   = q.question;
  document.getElementById('quizFeedback').style.display = 'none';
  document.getElementById('nextBtn').style.display      = 'none';
  document.getElementById('quizOptions').innerHTML = Object.entries(q.options).map(([k, v]) =>
    `<button class="quiz-option" data-key="${k}" onclick="submitAnswer('${q.id}','${k}',this)">
       <span class="opt-key">${k}</span>${v}
     </button>`
  ).join('');

  // Track topic
  if (!quizTopicMap[q.topic]) quizTopicMap[q.topic] = { correct: 0, total: 0 };
  quizTopicMap[q.topic].total++;

  // Timer
  updateTimerDisplay();
  quizTimer = setInterval(() => {
    quizTimeLeft--;
    updateTimerDisplay();
    if (quizTimeLeft <= 0) {
      clearInterval(quizTimer);
      handleTimeout(q);
    }
  }, 1000);
}

function updateTimerDisplay() {
  document.getElementById('timerNum').textContent = quizTimeLeft;
  const wrap = document.getElementById('timerDisplay');
  wrap.className = 'timer-counter' + (quizTimeLeft <= 10 ? ' urgent' : '');
}

function handleTimeout(q) {
  document.querySelectorAll('.quiz-option').forEach(b => {
    b.disabled = true;
    if (b.dataset.key === q.correct) b.classList.add('correct');
  });
  quizWrong++;
  quizStreak = 0;
  const fb = document.getElementById('quizFeedback');
  fb.innerHTML = `<div class="fb-header">⏰ Time's up!</div>Correct answer: <strong>${q.correct}) ${q.options[q.correct]}</strong>`;
  fb.className = 'quiz-feedback wrong';
  fb.style.display = 'block';
  document.getElementById('nextBtn').style.display = 'inline-flex';
}

async function submitAnswer(qid, answer, btn) {
  clearInterval(quizTimer);
  document.querySelectorAll('.quiz-option').forEach(b => b.disabled = true);

  const fb = document.getElementById('quizFeedback');
  fb.innerHTML = `<div style="display:flex;align-items:center;gap:8px;color:var(--gray);">
    <div class="typing-bubble">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div> AI is evaluating your answer...
  </div>`;
  fb.className = 'quiz-feedback';
  fb.style.display = 'block';

  try {
    const res    = await fetch('/api/quiz/submit', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: qid, answer })
    });
    const result = await res.json();

    // Mark options
    document.querySelectorAll('.quiz-option').forEach(b => {
      if (b.dataset.key === result.correct_key) b.classList.add('correct');
      if (b.dataset.key === result.user_key && !result.is_correct) b.classList.add('wrong');
    });

    if (result.is_correct) {
      const bonus = Math.max(0, quizTimeLeft);
      quizScore  += 10 + bonus;
      quizCorrect++;
      quizStreak++;
      if (quizStreak > quizBestStreak) quizBestStreak = quizStreak;
      if (quizTopicMap[result.topic]) quizTopicMap[result.topic].correct++;
      fb.innerHTML = `<div class="fb-header">✅ Correct! +${10 + bonus} pts${bonus > 0 ? ` (${bonus}s speed bonus)` : ''}</div>${result.explanation}`;
      fb.className = 'quiz-feedback correct';
    } else {
      quizWrong++;
      quizStreak = 0;
      fb.innerHTML = `<div class="fb-header">❌ Not quite — correct: ${result.correct_key}) ${result.correct_text}</div>${result.explanation}`;
      fb.className = 'quiz-feedback wrong';
    }

    document.getElementById('liveScore').textContent   = quizScore;
    document.getElementById('liveCorrect').textContent = quizCorrect;
    document.getElementById('liveWrong').textContent   = quizWrong;

    if (quizStreak >= 2) {
      document.getElementById('streakCounter').style.display = 'flex';
      document.getElementById('streakNum').textContent = quizStreak + '🔥';
    }

    document.getElementById('nextBtn').style.display = 'inline-flex';
  } catch(e) {
    fb.innerHTML = 'Error evaluating answer. Click Next to continue.';
    document.getElementById('nextBtn').style.display = 'inline-flex';
  }
}

function nextQuestion() { quizIndex++; showQuestion(); }

function quitQuiz() {
  clearInterval(quizTimer);
  if (quizIndex > 0 && !confirm('Quit the quiz? Your progress will be lost.')) return;
  resetQuizSetup();
}

function resetQuizSetup() {
  clearInterval(quizTimer);
  document.getElementById('quizSetup').style.display  = 'block';
  document.getElementById('quizActive').style.display = 'none';
  document.getElementById('quizResult').style.display = 'none';
  loadQuizStats();
}

async function showQuizResult() {
  clearInterval(quizTimer);
  const total    = quizQuestions.length;
  const accuracy = total > 0 ? Math.round((quizCorrect / total) * 100) : 0;

  document.getElementById('quizActive').style.display = 'none';
  document.getElementById('quizResult').style.display = 'block';

  // Emoji + message
  let emoji = '😔', msg = 'Keep studying — every attempt builds knowledge!';
  if (accuracy >= 90) { emoji = '🏆'; msg = 'Outstanding! You are a telecom expert!'; }
  else if (accuracy >= 70) { emoji = '🎉'; msg = 'Great job! Solid telecom knowledge!'; }
  else if (accuracy >= 50) { emoji = '👍'; msg = 'Good effort! A bit more practice and you will ace it!'; }

  document.getElementById('resultEmoji').textContent    = emoji;
  document.getElementById('quizFinalScore').textContent = quizCorrect + '/' + total;
  document.getElementById('resultMsg').textContent      = msg;
  document.getElementById('resAccuracy').textContent    = accuracy + '%';
  document.getElementById('resCorrect').textContent     = quizCorrect;
  document.getElementById('resWrong').textContent       = quizWrong;
  document.getElementById('resStreak').textContent      = quizBestStreak + '🔥';

  // Topic breakdown
  const rows = Object.entries(quizTopicMap).map(([topic, data]) => {
    const pct   = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;
    const color = pct >= 70 ? '#10B981' : pct >= 40 ? '#F97316' : '#EF4444';
    return `<div class="topic-row">
      <span class="topic-row-name" title="${topic}">${topic}</span>
      <div class="topic-row-bar-wrap"><div class="topic-row-bar" style="width:${pct}%;background:${color};"></div></div>
      <span class="topic-row-score" style="color:${color}">${data.correct}/${data.total}</span>
    </div>`;
  }).join('');
  document.getElementById('topicBreakdown').innerHTML =
    `<h4>Performance by topic</h4>${rows}`;

  // Save score
  try {
    await fetch('/api/quiz/score', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score: quizCorrect, total, difficulty: quizDiff })
    });
    loadQuizStats();
  } catch(e) { console.error(e); }
}

async function loadQuizStats() {
  try {
    const scores = await apiFetch('/api/quiz/history');
    if (!scores || !scores.length) return;
    const best   = Math.max(...scores.map(s => s.total > 0 ? Math.round(s.score / s.total * 100) : 0));
    const avgAcc = Math.round(scores.reduce((a, s) => a + (s.total > 0 ? s.score / s.total * 100 : 0), 0) / scores.length);
    document.getElementById('statBest').textContent     = best + '%';
    document.getElementById('statAttempts').textContent = scores.length;
    document.getElementById('statAvg').textContent      = avgAcc + '%';
  } catch(e) { console.error(e); }
}

async function loadQuizHistory() {
  try {
    const scores = await apiFetch('/api/quiz/history');
    const el     = document.getElementById('quizHistoryContainer');
    if (!scores || !scores.length) {
      el.innerHTML = '<p style="color:var(--gray);text-align:center;padding:40px;">No quiz attempts yet. Take your first quiz!</p>';
      return;
    }
    el.innerHTML = `
      <h3 style="margin-bottom:16px;"><i class="fas fa-history"></i> Quiz History</h3>
      <table class="quiz-history-table">
        <thead>
          <tr>
            <th>Date</th><th>Score</th><th>Accuracy</th><th>Difficulty</th>
          </tr>
        </thead>
        <tbody>
          ${scores.map(s => `
            <tr>
              <td>${new Date(s.date).toLocaleDateString()}</td>
              <td><strong>${s.score}/${s.total}</strong></td>
              <td>${Math.round(s.score / s.total * 100)}%</td>
              <td><span class="badge">${s.difficulty}</span></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch(e) { console.error(e); }
}

// Keyboard shortcuts A/B/C/D
document.addEventListener('keydown', e => {
  const active = document.getElementById('quizActive');
  if (!active || active.style.display === 'none') return;
  const key = e.key.toUpperCase();
  if (!['A','B','C','D'].includes(key)) return;
  const btn = document.querySelector(`.quiz-option[data-key="${key}"]:not(:disabled)`);
  if (btn) btn.click();
});

// ════════════════════════════════════════════
//  AI TUTOR
// ════════════════════════════════════════════

async function sendChat() {
  const ta  = document.getElementById('chatInput');
  const msg = ta.value.trim();
  if (!msg) return;

  document.getElementById('chatSuggestions').style.display = 'none';
  appendChat('user', msg);
  ta.value = '';
  ta.style.height = 'auto';
  updateCharCount(ta);
  chatHistory.push({ role: 'user', content: msg });

  const typingEl = appendTyping();
  document.getElementById('sendBtn').disabled = true;

  try {
    const res  = await fetch('/api/quiz/chat', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(-8) })
    });
    const data  = await res.json();
    const reply = data.reply || 'Sorry, I could not respond right now.';
    typingEl.remove();
    appendChat('bot', reply);
    chatHistory.push({ role: 'assistant', content: reply });
  } catch(e) {
    typingEl.remove();
    appendChat('bot', '❌ Connection error. Please try again.');
  }

  document.getElementById('sendBtn').disabled = false;
}

function appendChat(role, text) {
  const wrap = document.getElementById('chatMessages');
  const now  = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const div  = document.createElement('div');
  div.className = `chat-msg ${role}`;
  const copyBtn = role === 'bot'
    ? `<button class="copy-msg-btn" onclick="copyMsg(this)" title="Copy">⧉</button>`
    : '';
  div.innerHTML = `<div class="chat-bubble">${copyBtn}${text}<div class="msg-time">${now}</div></div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}

function appendTyping() {
  const wrap = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'chat-msg bot';
  div.innerHTML = `<div class="chat-bubble"><div class="typing-bubble">
    <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
  </div></div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}

function copyMsg(btn) {
  const text = btn.parentElement.innerText
    .replace(/⧉/g, '')
    .replace(/\d{1,2}:\d{2}\s*(AM|PM)?/gi, '')
    .trim();
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✓';
    setTimeout(() => btn.textContent = '⧉', 1500);
  });
}

function useSuggestion(btn) {
  document.getElementById('chatInput').value = btn.textContent;
  sendChat();
}

function askTopic(topic) {
  switchPage('tutor');
  setTimeout(() => {
    document.getElementById('chatInput').value =
      `Explain ${topic} in detail with real-world examples and use cases`;
    sendChat();
  }, 100);
}

function clearChat() {
  if (!confirm('Clear chat history?')) return;
  chatHistory = [];
  document.getElementById('chatMessages').innerHTML = `
    <div class="chat-msg bot">
      <div class="chat-bubble">
        Chat cleared! Ask me anything about telecom.
        <div class="msg-time">Just now</div>
      </div>
    </div>`;
  document.getElementById('chatSuggestions').style.display = 'flex';
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 130) + 'px';
}

function updateCharCount(el) {
  const len = el.value.length;
  const el2 = document.getElementById('charCount');
  el2.textContent = `${len}/500`;
  el2.className   = len > 450 ? 'char-count at-limit' : len > 380 ? 'char-count near-limit' : 'char-count';
}

// ════════════════════════════════════════════
//  UTILITIES
// ════════════════════════════════════════════

async function apiFetch(url) {
  try {
    const res = await fetch(url, { credentials: 'include' });
    if (res.status === 401) {
      showToast('Session expired. Please login again.', 'error');
      handleLogout();
      return null;
    }
    return await res.json();
  } catch(e) {
    console.error('apiFetch error:', url, e);
    return null;
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setBar(barId, pctId, pct) {
  const bar = document.getElementById(barId);
  const lbl = document.getElementById(pctId);
  if (bar) bar.style.width = pct + '%';
  if (lbl) lbl.textContent = pct + '%';
}

function toggleMenu(forceClose = false) {
  const menu = document.getElementById('userMenu');
  if (forceClose) { menu.classList.add('hidden'); return; }
  menu.classList.toggle('hidden');
}

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className   = `toast ${type}`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 4000);
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

function hideError(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

function setLoading(btn, label) {
  btn.dataset.orig = btn.innerHTML;
  btn.innerHTML    = `<i class="fas fa-spinner fa-spin"></i> ${label}`;
  btn.disabled     = true;
}

function resetLoading(btn, html) {
  btn.innerHTML = html;
  btn.disabled  = false;
}

// Close dropdown on outside click
document.addEventListener('click', e => {
  const menu = document.getElementById('userMenu');
  const sec  = document.querySelector('.user-section');
  if (menu && sec && !sec.contains(e.target)) menu.classList.add('hidden');
});

console.log('Telecomm Intelligence Platform loaded');