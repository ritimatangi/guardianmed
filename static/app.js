/* ══════════════════════════════════════════════════════════
   GuardianMed — app.js
   Live updates, score animation, voice assistant,
   multi-patient, AI suggestions, dark mode, notifications
   ══════════════════════════════════════════════════════════ */

// ── Utility ──────────────────────────────────────────────
function showToast(msg, type = '') {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3200);
}

async function api(path, opts = {}) {
    try {
        const o = { headers: { 'Content-Type': 'application/json' }, ...opts };
        if (o.body && typeof o.body === 'object') o.body = JSON.stringify(o.body);
        const res = await fetch(path, o);
        return res.json();
    } catch (e) {
        // Offline fallback
        const offlineBanner = document.getElementById('offline-banner');
        if (offlineBanner) offlineBanner.style.display = 'block';
        return null;
    }
}


// ══════════════════════════════════════════════════════════
// DARK MODE
// ══════════════════════════════════════════════════════════

function initDarkMode() {
    const btn = document.getElementById('dark-toggle');
    if (!btn) return;

    // Restore saved preference
    if (localStorage.getItem('gm-dark') === 'true') {
        document.body.classList.add('dark-mode');
        btn.textContent = '☀️';
    }

    btn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('gm-dark', isDark);
        btn.textContent = isDark ? '☀️' : '🌙';
        showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'info');
    });
}


// ══════════════════════════════════════════════════════════
// TRUST / APPROVAL MODAL
// ══════════════════════════════════════════════════════════

function showTrustModal(title, description, onApprove, onCancel) {
    const modal = document.getElementById('trust-modal');
    const titleEl = document.getElementById('modal-title');
    const descEl = document.getElementById('modal-desc');
    const approveBtn = document.getElementById('modal-approve');
    const cancelBtn = document.getElementById('modal-cancel');

    if (!modal) return;

    titleEl.textContent = title;
    descEl.textContent = description;
    modal.style.display = 'flex';

    // Clone buttons to clear old listeners
    const newApprove = approveBtn.cloneNode(true);
    const newCancel = cancelBtn.cloneNode(true);
    approveBtn.replaceWith(newApprove);
    cancelBtn.replaceWith(newCancel);

    newApprove.addEventListener('click', () => {
        modal.style.display = 'none';
        if (onApprove) onApprove();
    });
    newCancel.addEventListener('click', () => {
        modal.style.display = 'none';
        if (onCancel) onCancel();
        showToast('Action cancelled', 'warn');
    });
}


// ══════════════════════════════════════════════════════════
// PUSH NOTIFICATION SIMULATION
// ══════════════════════════════════════════════════════════

async function simulateNotifications() {
    const data = await api('/api/notifications');
    if (!data || !data.length) return;

    // Show notifications as toasts with delay
    data.forEach((n, i) => {
        setTimeout(() => {
            const type = n.type === 'alert' ? 'warn' : n.type === 'warning' ? 'error' : 'info';
            showToast(`${n.icon} ${n.title}: ${n.message}`, type);
        }, 3000 + i * 4000);
    });
}


// ══════════════════════════════════════════════════════════
// FINGERPRINT SIMULATION
// ══════════════════════════════════════════════════════════

function initFingerprint() {
    const btn = document.getElementById('fingerprint-btn');
    if (!btn) return;

    btn.addEventListener('click', () => {
        btn.textContent = '⏳';
        setTimeout(() => {
            btn.textContent = '✅';
            showToast('✅ Biometric authentication successful!');
            setTimeout(() => { btn.textContent = '🔐'; }, 2000);
        }, 1200);
    });
}


// ══════════════════════════════════════════════════════════
// CAREGIVER DASHBOARD
// ══════════════════════════════════════════════════════════

let adherenceChart = null;
let prevScore = null;

async function refreshAll() {
    // Run all updates in parallel for speed and responsiveness
    await Promise.all([
        loadGuardianScore(),
        loadSchedule(),
        loadAlerts(),
        loadAISuggestions(),
        loadMLPrediction(),
        loadPatientHistory()
    ]);
}

function initCaregiverDashboard() {
    initDarkMode();
    refreshAll();
    loadMedicines();
    loadPatterns();
    setupChat();
    document.getElementById('schedule-date').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    // Live polling — every 15 seconds (real-time, no fake simulation)
    setInterval(refreshAll, 15000);
    setInterval(loadPatterns, 60000);
}



// ── Guardian Score ────────────────────────────────────────
async function loadGuardianScore() {
    const data = await api('/api/guardian-score');
    if (!data) return;

    const scoreEl = document.getElementById('score-text');
    const ringEl = document.getElementById('score-ring-fill');
    const badgeEl = document.getElementById('score-level-badge');
    const breakdownEl = document.getElementById('score-breakdown');
    const reasonsEl = document.getElementById('score-reasons');
    const explEl = document.getElementById('score-explanation');

    // Animate score number
    const current = parseInt(scoreEl.textContent) || 0;
    animateNumber(scoreEl, current, data.score, 800);

    // Animate ring
    const circumference = 2 * Math.PI * 70;
    const offset = circumference - (data.score / 100) * circumference;
    ringEl.style.strokeDasharray = circumference;
    ringEl.style.strokeDashoffset = offset;
    ringEl.style.stroke = data.color;

    // Badge
    badgeEl.textContent = data.level.replace('_', ' ');
    badgeEl.className = 'badge badge-' + data.level;

    // Explanation
    if (explEl) {
        if (data.score >= 80) explEl.textContent = '✅ Excellent adherence. Keep up the great work!';
        else if (data.score >= 50) explEl.textContent = `⚠️ ${data.reasons[0] || 'Some doses missed. Room for improvement.'}`;
        else explEl.textContent = `🚨 Score decreased due to ${data.reasons[0] || 'multiple missed doses'}.`;
    }

    // Breakdown
    breakdownEl.innerHTML = `
        <div class="breakdown-item"><span class="breakdown-val">${data.breakdown.adherence}%</span>Adherence</div>
        <div class="breakdown-item"><span class="breakdown-val">${data.breakdown.timing_accuracy}%</span>Timing</div>
        <div class="breakdown-item"><span class="breakdown-val">${data.breakdown.risk_flags}%</span>Risk</div>
    `;

    // Reasons
    reasonsEl.innerHTML = data.reasons.slice(0, 3).map(r => `<li>${r}</li>`).join('');

    // Toast on score change
    if (prevScore !== null && prevScore !== data.score) {
        const diff = data.score - prevScore;
        const arrow = diff > 0 ? '↑' : '↓';
        showToast(`Guardian Score ${arrow} ${data.score} (${diff > 0 ? '+' : ''}${diff})`,
                  diff > 0 ? '' : 'warn');
    }
    prevScore = data.score;
}

function animateNumber(el, from, to, duration) {
    const start = performance.now();
    const step = (ts) => {
        const p = Math.min((ts - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(from + (to - from) * eased);
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}


// ── AI Suggestions ───────────────────────────────────────
async function loadAISuggestions() {
    const data = await api('/api/ai/suggestions');
    const container = document.getElementById('ai-suggestions');
    if (!data || !container) return;

    container.innerHTML = data.map(s => `
        <div class="ai-sug-item">
            <div class="ai-sug-icon">${s.icon}</div>
            <div class="ai-sug-body">
                <div class="ai-sug-title">${s.title}
                    <span class="ai-sug-severity sev-${s.severity}">${s.severity}</span>
                </div>
                <div class="ai-sug-desc">${s.description}</div>
                <div class="ai-sug-action-text">→ ${s.action}</div>
                <div class="ai-sug-actions">
                    ${s.requires_approval ?
                        `<button class="btn btn-sm btn-primary" onclick="approveAISuggestion('${s.id}', '${s.action.replace(/'/g, "\\'")}')">✔ Approve</button>
                         <button class="btn btn-sm btn-outline" onclick="dismissAISuggestion(this)">✗ Dismiss</button>` :
                        `<button class="btn btn-sm btn-outline" onclick="autoApproveAISuggestion('${s.id}')">✔ Apply</button>
                         <button class="btn btn-sm btn-outline" onclick="dismissAISuggestion(this)">✗ Dismiss</button>`
                    }
                </div>
            </div>
        </div>
    `).join('');
}

async function approveAISuggestion(sugId, actionDesc) {
    showTrustModal(
        'AI suggests an action. Approve?',
        actionDesc,
        async () => {
            const result = await api('/api/ai/approve', { method: 'POST', body: { suggestion_id: sugId } });
            if (result) showToast(result.message);
            loadAISuggestions();
        },
        null
    );
}

async function autoApproveAISuggestion(sugId) {
    const result = await api('/api/ai/approve', { method: 'POST', body: { suggestion_id: sugId } });
    if (result) showToast(result.message);
}

function dismissAISuggestion(btn) {
    const item = btn.closest('.ai-sug-item');
    if (item) {
        item.style.opacity = '0';
        item.style.transform = 'translateX(40px)';
        item.style.transition = 'all 0.3s ease';
        setTimeout(() => item.remove(), 300);
        showToast('Suggestion dismissed');
    }
}


// ── ML Prediction ────────────────────────────────────────
async function loadMLPrediction() {
    const container = document.getElementById('ml-content');
    if (!container) return;

    const data = await api('/api/ml/predict');
    if (!data) return;

    const pct = data.probability;
    const barWidth = Math.min(pct, 100);

    container.innerHTML = `
        <div class="ml-result">
            <div class="ml-gauge">
                <div class="ml-gauge-bar" style="width:${barWidth}%; background:${data.color};"></div>
            </div>
            <div class="ml-prob">
                <span class="ml-prob-num" style="color:${data.color};">${data.icon} ${pct}%</span>
                <span class="ml-risk-badge ml-risk-${data.risk_level}">${data.risk_level.toUpperCase()} RISK</span>
            </div>
            <p class="ml-explanation">${data.explanation}</p>
            <div class="ml-features">
                <span class="ml-feat">Missed (3d): <strong>${data.features_used.missed_last_3_days}</strong></span>
                <span class="ml-feat">Avg Delay: <strong>${data.features_used.avg_delay_minutes} min</strong></span>
                <span class="ml-feat">Adherence: <strong>${data.features_used.adherence_rate}%</strong></span>
            </div>
            ${data.feature_importance ? `
                <div class="ml-importance">
                    <small>Feature Importance:</small>
                    ${data.feature_importance.map(f => `
                        <div class="ml-imp-row">
                            <span class="ml-imp-name">${f.feature.replace(/_/g, ' ')}</span>
                            <div class="ml-imp-bar-bg"><div class="ml-imp-bar" style="width:${f.importance}%;"></div></div>
                            <span class="ml-imp-val">${f.importance}%</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
}


// ── Patient History ──────────────────────────────────────
async function loadPatientHistory() {
    const container = document.getElementById('patient-history');
    if (!container) return;

    const data = await api('/api/patient/history');
    if (!data || !data.length) {
        container.innerHTML = '<p class="loading-cell">No activity today yet.</p>';
        return;
    }

    container.innerHTML = data.map(h => `
        <div class="history-item history-${h.status}">
            <span class="history-time">${h.time}</span>
            <span class="history-icon">${h.icon}</span>
            <span class="history-med">${h.medicine} <small>${h.dose}</small></span>
            <span class="history-detail">${h.detail}</span>
        </div>
    `).join('');
}


// ── Schedule ─────────────────────────────────────────────
async function loadSchedule() {
    const data = await api('/api/schedule/today');
    const tbody = document.getElementById('schedule-body');
    if (!data || !tbody) return;

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No doses scheduled today.</td></tr>';
        return;
    }

    tbody.innerHTML = data.map(d => `
        <tr>
            <td><strong>${d.name}</strong></td>
            <td>${d.dose}</td>
            <td>${d.scheduled_time}</td>
            <td><span class="status-badge status-${d.status}">${d.status}</span></td>
            <td>
                ${(d.status === 'upcoming' || d.status === 'due') ? `
                    <button class="btn btn-sm btn-primary" onclick="markDose(${d.log_id}, 'taken')">✓ Taken</button>
                    <button class="btn btn-sm btn-danger" onclick="markDose(${d.log_id}, 'missed')" style="margin-left:4px;">✗ Miss</button>
                ` : '—'}
            </td>
        </tr>
    `).join('');
}

async function markDose(logId, action) {
    try {
        // Make API call to log the dose
        const endpoint = action === 'taken' ? '/api/dose/log' : '/api/dose/miss';
        const response = await api(endpoint, { 
            method: 'POST', 
            body: { log_id: logId } 
        });
        
        if (!response) {
            showToast('Error: Could not connect to server', 'error');
            return;
        }

        // Show success message
        const toastType = action === 'taken' ? 'success' : 'warn';
        showToast(action === 'taken' ? '✅ Dose marked as taken' : '⚠️ Dose marked as missed', toastType);

        // Refresh all components sequentially to ensure proper updates
        await loadSchedule();      // Update schedule first
        await loadGuardianScore(); // Then update score
        await loadMLPrediction();  // Then update ML prediction
        await loadAISuggestions(); // Get new suggestions
        await loadMedicines();     // Update medicines list
        await loadAlerts();        // Update alerts
        
    } catch (error) {
        console.error('Error marking dose:', error);
        showToast('Error updating dose status', 'error');
    }
}


// ── Medicines ────────────────────────────────────────────
async function loadMedicines() {
    const meds = await api('/api/medicines');
    const list = document.getElementById('meds-list');
    if (!meds || !list) return;

    if (!meds.length) {
        list.innerHTML = '<p class="loading-cell">No medicines added yet.</p>';
        return;
    }

    list.innerHTML = meds.map(m => {
        const times = JSON.parse(m.times || '[]').join(', ');
        return `
            <div class="med-card">
                <div class="med-info">
                    <h4>${m.name} <span style="color:var(--text-muted);font-weight:400;">${m.dose}</span></h4>
                    <p>${m.frequency} · ${times}${m.drug_class ? ' · ' + m.drug_class : ''}</p>
                </div>
                <div class="med-actions">
                    <a href="/add-medicine?id=${m.id}" class="btn btn-sm btn-outline">Edit</a>
                    <button class="btn btn-sm btn-danger" onclick="deleteMedicine(${m.id})">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

async function deleteMedicine(id) {
    if (!confirm('Delete this medicine?')) return;
    await api(`/api/medicines/${id}`, { method: 'DELETE' });
    showToast('Medicine removed');
    loadMedicines();
    loadSchedule();
    setTimeout(loadGuardianScore, 500);
}


// ── Alerts ───────────────────────────────────────────────
async function loadAlerts() {
    const flags = await api('/api/alerts');
    const list = document.getElementById('alerts-list');
    if (!list) return;

    if (!flags || !flags.length) {
        list.innerHTML = '<div class="no-alerts">✓ No active alerts</div>';
        return;
    }

    list.innerHTML = flags.map(f => `
        <div class="alert-item alert-${f.severity}">
            <div class="alert-severity">${f.severity} severity</div>
            <div>${f.reason}</div>
        </div>
    `).join('');
}


// ── Patterns / Chart ─────────────────────────────────────
async function loadPatterns() {
    const data = await api('/api/behaviour/patterns');
    if (!data) return;
    renderAdherenceChart(data.weekly_adherence);
    const insights = document.getElementById('pattern-insights');
    if (insights) insights.innerHTML = data.insights.map(i => `<div class="insight-tag">${i}</div>`).join('');
}

function renderAdherenceChart(weekly) {
    const ctx = document.getElementById('adherence-chart');
    if (!ctx) return;

    const labels = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        labels.push(d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric' }));
    }

    if (adherenceChart) adherenceChart.destroy();

    const isDark = document.body.classList.contains('dark-mode');
    adherenceChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Adherence %',
                data: weekly,
                borderColor: '#1D9E75',
                backgroundColor: 'rgba(29,158,117,0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointBackgroundColor: '#1D9E75',
                pointBorderColor: isDark ? '#1A1D27' : '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1a1a',
                    titleFont: { family: 'Inter' },
                    bodyFont: { family: 'Inter' },
                    callbacks: { label: ctx => ctx.parsed.y + '%' }
                }
            },
            scales: {
                y: {
                    min: 0, max: 100,
                    ticks: { callback: v => v + '%', font: { family: 'Inter', size: 11 }, color: isDark ? '#9CA3AF' : '#6B7280' },
                    grid: { color: isDark ? '#2D3140' : '#f0f0f0' }
                },
                x: {
                    ticks: { font: { family: 'Inter', size: 11 }, color: isDark ? '#9CA3AF' : '#6B7280' },
                    grid: { display: false }
                }
            }
        }
    });
}


// ── Chat ─────────────────────────────────────────────────
function setupChat() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    if (!input || !sendBtn) return;

    sendBtn.addEventListener('click', () => sendChat());
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendChat();
    });
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendChat(msg, 'user');
    input.value = '';

    const data = await api('/api/ai/chat', { method: 'POST', body: { message: msg } });
    if (data) appendChat(data.reply, 'bot');

    // Show reasoning
    if (data && data.reasoning && data.reasoning.length) {
        const chain = document.getElementById('reasoning-chain');
        const list = document.getElementById('reasoning-list');
        if (chain && list) {
            chain.style.display = 'block';
            list.innerHTML = data.reasoning.map(r => `<li>${r}</li>`).join('');
        }
    }

    if (msg.toLowerCase().includes('mark') || msg.toLowerCase().includes('taken')) {
        setTimeout(() => { loadSchedule(); loadGuardianScore(); }, 500);
    }
}

function appendChat(text, who) {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'chat-msg ' + who;
    div.innerHTML = `<div class="msg-content">${text}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}


// ══════════════════════════════════════════════════════════
// ELDERLY MODE
// ══════════════════════════════════════════════════════════

let elderlyNextLog = null;

function refreshElderlyAll() {
    loadElderlyScore();
    loadElderlyNextMed();
    loadElderlyAISuggestion();
}

function initElderlyMode() {
    initDarkMode();
    initFingerprint();
    refreshElderlyAll();
    loadElderlyMeds();
    setupElderlyTabs();
    setupVoice();

    // Live polling — every 15 seconds (no fake simulation)
    setInterval(refreshElderlyAll, 15000);

    // Offline detection
    window.addEventListener('offline', () => {
        const b = document.getElementById('offline-banner');
        if (b) b.style.display = 'block';
        showToast('📡 You are offline', 'warn');
    });
    window.addEventListener('online', () => {
        const b = document.getElementById('offline-banner');
        if (b) b.style.display = 'none';
        showToast('✅ Back online');
    });
}

async function loadElderlyScore() {
    const data = await api('/api/guardian-score');
    if (!data) return;

    const scoreEl = document.getElementById('e-score-text');
    const ringEl = document.getElementById('e-score-ring');
    const levelEl = document.getElementById('e-score-level');
    const explEl = document.getElementById('e-score-explanation');

    const current = parseInt(scoreEl.textContent) || 0;
    animateNumber(scoreEl, current, data.score, 800);

    const circumference = 2 * Math.PI * 85;
    const offset = circumference - (data.score / 100) * circumference;
    ringEl.style.strokeDasharray = circumference;
    ringEl.style.strokeDashoffset = offset;
    ringEl.style.stroke = data.color;

    levelEl.textContent = data.level === 'safe' ? '✅ You are doing well!' :
                          data.level === 'caution' ? '⚠️ Needs some attention' :
                          '🚨 Please take your medicines';
    levelEl.style.color = data.color;

    // Explanation
    if (explEl) {
        if (data.score >= 80) explEl.textContent = 'Great job! You are taking your medicines on time.';
        else if (data.score >= 50) explEl.textContent = data.reasons[0] || 'Try to take your medicines on time.';
        else explEl.textContent = 'Your score is low. Please take your medicines. Ask for help if needed.';
    }
}

async function loadElderlyNextMed() {
    const schedule = await api('/api/schedule/today');
    if (!schedule) return;

    const upcoming = schedule.filter(s => s.status === 'upcoming');
    const infoEl = document.getElementById('next-med-info');
    const takeBtn = document.getElementById('btn-take');
    const missBtn = document.getElementById('btn-miss');

    if (upcoming.length > 0) {
        const next = upcoming[0];
        elderlyNextLog = next;
        infoEl.innerHTML = `
            <strong>${next.name}</strong> — ${next.dose}
            <span class="next-med-time">⏰ ${next.scheduled_time}</span>
        `;
        takeBtn.disabled = false;
        missBtn.disabled = false;
    } else {
        elderlyNextLog = null;
        infoEl.innerHTML = '<div class="no-more-meds">✅ All done for today!</div>';
        takeBtn.disabled = true;
        missBtn.disabled = true;
    }

    takeBtn.onclick = async () => {
        if (!elderlyNextLog) return;
        await api('/api/dose/log', { method: 'POST', body: { log_id: elderlyNextLog.log_id } });
        showToast('✅ Marked as taken!');
        loadElderlyNextMed();
        loadElderlyScore();
        loadElderlyAISuggestion();
    };
    missBtn.onclick = async () => {
        if (!elderlyNextLog) return;
        await api('/api/dose/miss', { method: 'POST', body: { log_id: elderlyNextLog.log_id } });
        showToast('Marked as missed', 'warn');
        loadElderlyNextMed();
        loadElderlyScore();
        loadElderlyAISuggestion();
    };
}

async function loadElderlyMeds() {
    const meds = await api('/api/medicines');
    const list = document.getElementById('elderly-meds-list');
    if (!meds || !list) return;

    if (!meds.length) {
        list.innerHTML = '<p style="font-size:22px;">No medicines found.</p>';
        return;
    }

    list.innerHTML = meds.map(m => {
        const times = JSON.parse(m.times || '[]').join(', ');
        return `
            <div class="elderly-med-card">
                <h3>${m.name}</h3>
                <p>${m.dose} · ${m.frequency}<br>🕐 ${times}</p>
            </div>
        `;
    }).join('');
}


// ── Elderly AI Suggestion ────────────────────────────────
async function loadElderlyAISuggestion() {
    const data = await api('/api/ai/suggestions');
    const card = document.getElementById('elderly-ai-card');
    const textEl = document.getElementById('elderly-ai-text');
    const approveBtn = document.getElementById('elderly-ai-approve');
    const dismissBtn = document.getElementById('elderly-ai-dismiss');
    if (!data || !card || !data.length) return;

    // Show the most important suggestion
    const important = data.find(s => s.severity === 'high') || data[0];
    card.style.display = 'block';
    textEl.textContent = `🧠 ${important.description}`;

    approveBtn.onclick = () => {
        if (important.requires_approval) {
            showTrustModal(
                'AI suggests an action. Approve?',
                important.action,
                async () => {
                    const result = await api('/api/ai/approve', { method: 'POST', body: { suggestion_id: important.id } });
                    if (result) showToast(result.message);
                    card.style.display = 'none';
                },
                null
            );
        } else {
            api('/api/ai/approve', { method: 'POST', body: { suggestion_id: important.id } })
                .then(r => { if (r) showToast(r.message); });
            card.style.display = 'none';
        }
    };
    dismissBtn.onclick = () => {
        card.style.display = 'none';
        showToast('Suggestion dismissed');
    };
}


function setupElderlyTabs() {
    document.querySelectorAll('.bnav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.bnav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
            document.getElementById(btn.dataset.tab).style.display = 'block';
        });
    });
}


// ══════════════════════════════════════════════════════════
// VOICE ASSISTANT (Web Speech API)
// ══════════════════════════════════════════════════════════

let recognition = null;
let isListening = false;

function setupVoice() {
    const voiceBtn = document.getElementById('btn-voice');
    const fallback = document.getElementById('voice-fallback');

    if (!voiceBtn) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceBtn.style.display = 'none';
        if (fallback) fallback.style.display = 'block';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        showTranscript(transcript);
        stopListening();

        const data = await api('/api/ai/chat', { method: 'POST', body: { message: transcript } });
        if (data) {
            showTTSResponse(data.reply);
            speak(data.reply);
        }

        if (transcript.toLowerCase().includes('mark') || transcript.toLowerCase().includes('took') || transcript.toLowerCase().includes('taken')) {
            setTimeout(() => { loadElderlyNextMed(); loadElderlyScore(); }, 800);
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech error:', event.error);
        stopListening();
        if (event.error === 'not-allowed') {
            showToast('Microphone access denied', 'error');
        }
    };

    recognition.onend = () => { stopListening(); };

    voiceBtn.addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
            stopListening();
        } else {
            startListening();
        }
    });
}

function startListening() {
    const btn = document.getElementById('btn-voice');
    btn.textContent = '🛑 Listening…';
    btn.classList.add('listening');
    isListening = true;
    recognition.start();
}

function stopListening() {
    const btn = document.getElementById('btn-voice');
    if (btn) {
        btn.textContent = '🎤 Talk to Me';
        btn.classList.remove('listening');
    }
    isListening = false;
}

function showTranscript(text) {
    const area = document.getElementById('transcript-area');
    const el = document.getElementById('transcript-text');
    if (area && el) {
        area.style.display = 'block';
        el.textContent = text;
    }
}

function showTTSResponse(text) {
    const area = document.getElementById('tts-area');
    const el = document.getElementById('tts-text');
    if (area && el) {
        area.style.display = 'block';
        el.textContent = text;
    }
}

function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.rate = 0.9;
        u.pitch = 1;
        u.lang = 'en-US';
        window.speechSynthesis.speak(u);
    }
}


// ══════════════════════════════════════════════════════════
// MEDICINE FORM
// ══════════════════════════════════════════════════════════

function initMedicineForm() {
    initDarkMode();
    const form = document.getElementById('medicine-form');
    const timesContainer = document.getElementById('times-input');
    const addTimeBtn = document.getElementById('add-time-btn');
    const medIdEl = document.getElementById('med-id');

    let times = [];

    if (medIdEl) {
        fetch('/api/medicines/' + medIdEl.value)
            .then(r => r.json())
            .catch(() => null);
    }

    const existingName = document.getElementById('med-name').value;
    if (existingName && medIdEl) {
        api('/api/medicines').then(meds => {
            if (!meds) return;
            const med = meds.find(m => m.id === parseInt(medIdEl.value));
            if (med) {
                times = JSON.parse(med.times || '[]');
                renderTimes();
            }
        });
    }

    if (!medIdEl) {
        addTimeSlot('08:00');
    }

    addTimeBtn.addEventListener('click', () => {
        addTimeSlot('12:00');
    });

    function addTimeSlot(defaultTime) {
        times.push(defaultTime);
        renderTimes();
    }

    function renderTimes() {
        timesContainer.innerHTML = times.map((t, i) => `
            <div class="time-chip">
                <input type="time" value="${t}" onchange="this.parentElement.dataset.time=this.value" style="border:none;font-size:14px;font-family:inherit;background:transparent;color:inherit;">
                <button type="button" onclick="this.parentElement.remove()" title="Remove">×</button>
            </div>
        `).join('');
    }

    renderTimes();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const timeChips = timesContainer.querySelectorAll('.time-chip input[type=time]');
        const collectedTimes = Array.from(timeChips).map(i => i.value).filter(Boolean);

        const payload = {
            name: document.getElementById('med-name').value.trim(),
            dose: document.getElementById('med-dose').value.trim(),
            frequency: document.getElementById('med-frequency').value,
            times: collectedTimes,
            drug_class: document.getElementById('med-class').value.trim(),
            notes: document.getElementById('med-notes').value.trim()
        };

        if (!payload.name || !payload.dose) {
            showToast('Name and dose are required', 'error');
            return;
        }

        if (medIdEl) {
            await api(`/api/medicines/${medIdEl.value}`, { method: 'PUT', body: payload });
            showToast('Medicine updated!');
        } else {
            await api('/api/medicines', { method: 'POST', body: payload });
            showToast('Medicine added!');
        }

        setTimeout(() => { window.location.href = '/caregiver'; }, 600);
    });
}


// ══════════════════════════════════════════════════════════
// SOS PAGE
// ══════════════════════════════════════════════════════════

async function initSOSPage() {
    initDarkMode();

    const meds = await api('/api/medicines');
    const tbody = document.getElementById('sos-medicines-body');
    if (meds && tbody) {
        tbody.innerHTML = meds.map(m => `
            <tr>
                <td><strong>${m.name}</strong></td>
                <td>${m.dose}</td>
                <td>${m.frequency}</td>
                <td>${m.notes || m.drug_class || '—'}</td>
            </tr>
        `).join('');
    }

    const score = await api('/api/guardian-score');
    if (score) {
        document.getElementById('sos-score').textContent = score.score;
        document.getElementById('sos-score').style.color = score.color;
        document.getElementById('sos-score-level').textContent = score.level.replace('_', ' ').toUpperCase();
        document.getElementById('sos-score-reason').textContent = score.reasons[0] || '';
    }
}
