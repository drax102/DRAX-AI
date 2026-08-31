// Drax AI Web Dashboard Controller (Production & Cloud Ready)

// Dynamic API URL Resolution (Priority: URL query ?api= -> localStorage -> window.DRAX_API_URL -> window.__DRAX_API_URL__ -> localhost -> default Render Cloud backend)
function getApiBase() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramApi = urlParams.get('api');
  if (paramApi) {
    localStorage.setItem('drax_api_url', paramApi.replace(/\/$/, ''));
    return paramApi.replace(/\/$/, '');
  }

  const stored = localStorage.getItem('drax_api_url');
  if (stored) return stored.replace(/\/$/, '');

  if (window.DRAX_API_URL) return window.DRAX_API_URL.replace(/\/$/, '');
  if (window.__DRAX_API_URL__) return window.__DRAX_API_URL__.replace(/\/$/, '');

  // If accessed locally in development alongside local backend
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return window.location.port && window.location.port !== '80'
      ? `${window.location.protocol}//${window.location.hostname}:${window.location.port}`
      : 'http://127.0.0.1:8765';
  }

  // Production Render Cloud Backend
  return 'https://drax-cloud-api.onrender.com';
}

let API_BASE = getApiBase();


document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initClock();
  initModals();
  initChat();
  initDevices();
  initTasks();
  initReminders();
  initFinance();
  initNews();
  initTelemetry();
});

// ── Tabs Navigation ──────────────────────────────────────────────────────────
function initTabs() {
  const buttons = document.querySelectorAll('.nav-btn');
  const panes = document.querySelectorAll('.tab-pane');
  const pageTitle = document.getElementById('page-title');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(`tab-${tabId}`);
      if (targetPane) targetPane.classList.add('active');
      pageTitle.innerText = btn.innerText.trim();

      // Trigger refreshes
      if (tabId === 'devices') loadDevices();
      if (tabId === 'tasks') loadTasks();
      if (tabId === 'reminders') loadReminders();
      if (tabId === 'finance') loadFinance();
      if (tabId === 'news') loadNews('world');
      if (tabId === 'system') loadTelemetry();
    });
  });
}

// ── Modals & API Settings ───────────────────────────────────────────────────
function initModals() {
  const pairModal = document.getElementById('pair-modal');
  const settingsModal = document.getElementById('settings-modal');

  const openPairBtn = document.getElementById('pair-modal-btn');
  const openPairBtn2 = document.getElementById('open-pair-btn');
  const cancelPairBtn = document.getElementById('cancel-pair-btn');
  const submitPairBtn = document.getElementById('submit-pair-btn');
  const pairingInput = document.getElementById('pairing-code-input');

  const settingsBtn = document.getElementById('settings-btn');
  const cancelSettingsBtn = document.getElementById('cancel-settings-btn');
  const saveSettingsBtn = document.getElementById('save-settings-btn');
  const apiUrlInput = document.getElementById('api-url-input');

  if (openPairBtn) openPairBtn.addEventListener('click', () => pairModal.classList.add('active'));
  if (openPairBtn2) openPairBtn2.addEventListener('click', () => pairModal.classList.add('active'));
  if (cancelPairBtn) cancelPairBtn.addEventListener('click', () => pairModal.classList.remove('active'));

  if (submitPairBtn) {
    submitPairBtn.addEventListener('click', async () => {
      const code = pairingInput.value.trim().toUpperCase();
      if (!code) return;
      submitPairBtn.innerText = 'Connecting...';
      try {
        const resp = await fetch(`${API_BASE}/api/pair/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pairing_code: code })
        });
        if (resp.ok) {
          alert('Workstation successfully paired!');
          pairModal.classList.remove('active');
          loadDevices();
        } else {
          const err = await resp.json();
          alert(`Pairing failed: ${err.detail || 'Invalid code'}`);
        }
      } catch (e) {
        alert(`Error contacting cloud API: ${e.message}`);
      } finally {
        submitPairBtn.innerText = 'Connect Device';
      }
    });
  }

  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      apiUrlInput.value = API_BASE;
      settingsModal.classList.add('active');
    });
  }

  if (cancelSettingsBtn) cancelSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('active'));

  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', () => {
      const newUrl = apiUrlInput.value.trim().replace(/\/$/, '');
      if (newUrl) {
        localStorage.setItem('drax_api_url', newUrl);
        API_BASE = newUrl;
        settingsModal.classList.remove('active');
        alert(`API Endpoint updated to: ${API_BASE}`);
        window.location.reload();
      }
    });
  }
}

// ── Clock ──────────────────────────────────────────────────────────────────
function initClock() {
  function update() {
    const now = new Date();
    const clockEl = document.getElementById('clock');
    if (clockEl) clockEl.innerText = now.toLocaleTimeString();
  }
  update();
  setInterval(update, 1000);
}

// ── Chat & Command Terminal ────────────────────────────────────────────────
function initChat() {
  const input = document.getElementById('command-input');
  const sendBtn = document.getElementById('send-btn');
  const voiceBtn = document.getElementById('voice-btn');
  const quickBrief = document.getElementById('quick-brief-btn');

  async function execute(cmd) {
    if (!cmd || !cmd.trim()) return;
    appendMessage(cmd, 'user');
    if (input) input.value = '';

    try {
      const resp = await fetch(`${API_BASE}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await resp.json();
      appendMessage(data.response || 'Executed successfully.', 'drax');
    } catch (err) {
      appendMessage(`Error contacting Drax Cloud: ${err.message}`, 'system');
    }
  }

  if (sendBtn && input) {
    sendBtn.addEventListener('click', () => execute(input.value));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') execute(input.value);
    });
  }

  if (quickBrief) {
    quickBrief.addEventListener('click', () => execute('give me my daily briefing'));
  }

  // Quick Chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      execute(chip.getAttribute('data-cmd'));
    });
  });

  // Web Speech Recognition for voice button
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognizer = new SpeechRecognition();
    recognizer.continuous = false;
    recognizer.interimResults = false;

    recognizer.onstart = () => {
      if (voiceBtn) voiceBtn.style.color = '#ff3366';
      appendMessage('🎤 Listening for voice instruction...', 'system');
    };

    recognizer.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (voiceBtn) voiceBtn.style.color = '#00f3ff';
      execute(transcript);
    };

    recognizer.onerror = () => {
      if (voiceBtn) voiceBtn.style.color = '#00f3ff';
    };

    recognizer.onend = () => {
      if (voiceBtn) voiceBtn.style.color = '#00f3ff';
    };

    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        recognizer.start();
      });
    }
  }
}

function appendMessage(text, type) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  div.innerText = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// ── Devices Tab ────────────────────────────────────────────────────────────
async function initDevices() {
  loadDevices();
}

async function loadDevices() {
  const container = document.getElementById('devices-grid');
  if (!container) return;

  try {
    const resp = await fetch(`${API_BASE}/api/devices`);
    const data = await resp.json();
    const devices = data.devices || [];

    if (devices.length === 0) {
      container.innerHTML = `
        <div class="card device-card">
          <div class="device-header">
            <i class="fa-brands fa-windows device-icon"></i>
            <div>
              <h3>My Windows Workstation</h3>
              <p class="status-online"><span class="status-indicator"></span> Standalone Local Mode</p>
            </div>
          </div>
          <div class="device-actions">
            <button class="device-cmd-btn" onclick="executeFromDevice('open chrome')">Open Chrome</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('open spotify')">Open Spotify</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('lock pc')">Lock Workstation</button>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = devices.map(d => `
      <div class="card device-card">
        <div class="device-header">
          <i class="fa-brands fa-windows device-icon"></i>
          <div>
            <h3>${d.name} (${d.device_id})</h3>
            <p class="${d.status === 'online' ? 'status-online' : ''}" style="color: ${d.status === 'online' ? '#00ff88' : '#8b949e'}">
              <span class="status-indicator" style="background: ${d.status === 'online' ? '#00ff88' : '#8b949e'}"></span>
              ${d.status === 'online' ? 'Online & Listening' : 'Offline'}
            </p>
          </div>
        </div>
        <div class="device-actions">
          <button class="device-cmd-btn" onclick="executeFromDevice('open chrome', '${d.device_id}')">Open Chrome</button>
          <button class="device-cmd-btn" onclick="executeFromDevice('open spotify', '${d.device_id}')">Open Spotify</button>
          <button class="device-cmd-btn" onclick="executeFromDevice('lock pc', '${d.device_id}')">Lock PC</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

window.executeFromDevice = async function(cmd, deviceId = null) {
  appendMessage(cmd, 'user');
  // Switch to chat tab
  const chatBtn = document.querySelector('[data-tab="chat"]');
  if (chatBtn) chatBtn.click();

  try {
    const resp = await fetch(`${API_BASE}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd, device_id: deviceId })
    });
    const data = await resp.json();
    appendMessage(data.response || 'Action sent to Windows workstation.', 'drax');
  } catch (e) {
    appendMessage(`Error: ${e.message}`, 'system');
  }
};

// ── Tasks ──────────────────────────────────────────────────────────────────
async function initTasks() {
  const addBtn = document.getElementById('add-task-btn');
  const input = document.getElementById('new-task-input');

  if (addBtn && input) {
    addBtn.addEventListener('click', async () => {
      const title = input.value.trim();
      if (!title) return;
      await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title })
      });
      input.value = '';
      loadTasks();
    });
  }

  loadTasks();
}

async function loadTasks() {
  const container = document.getElementById('tasks-list');
  if (!container) return;
  try {
    const resp = await fetch(`${API_BASE}/tasks`);
    const data = await resp.json();
    const tasks = data.tasks || [];
    if (tasks.length === 0) {
      container.innerHTML = '<div class="empty-state">No pending tasks. Add a task above or say "Add a task".</div>';
      return;
    }
    container.innerHTML = tasks.map(t => `
      <div class="card">
        <h3>#${t.id}: ${t.title}</h3>
        <p style="color: ${t.status === 'completed' ? '#00ff88' : '#ffaa00'}; font-weight: bold; margin-top: 8px;">
          Status: ${t.status.toUpperCase()}
        </p>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="empty-state">Failed to load tasks: ${err.message}</div>`;
  }
}

// ── Reminders & Alarms ─────────────────────────────────────────────────────
async function initReminders() {
  loadReminders();
}

async function loadReminders() {
  const remContainer = document.getElementById('reminders-list');
  const alarmContainer = document.getElementById('alarms-list');

  try {
    const remResp = await fetch(`${API_BASE}/reminders`);
    const remData = await remResp.json();
    const rems = remData.reminders || [];
    if (remContainer) {
      remContainer.innerHTML = rems.length ? rems.map(r => `
        <div class="card">
          <h3>🔔 ${r.message}</h3>
          <p style="color: var(--accent-cyan); margin-top: 6px;">Due: ${r.remind_at}</p>
        </div>
      `).join('') : '<div class="empty-state">No active reminders.</div>';
    }

    const alarmResp = await fetch(`${API_BASE}/alarms`);
    const alarmData = await alarmResp.json();
    const alarms = alarmData.alarms || [];
    if (alarmContainer) {
      alarmContainer.innerHTML = alarms.length ? alarms.map(a => `
        <div class="card">
          <h3>⏰ ${a.time_str}</h3>
          <p style="color: var(--text-muted); margin-top: 6px;">${a.label}</p>
        </div>
      `).join('') : '<div class="empty-state">No active alarms.</div>';
    }
  } catch (err) {
    console.error(err);
  }
}

// ── Finance & Stocks ───────────────────────────────────────────────────────
async function initFinance() {
  const btn = document.getElementById('stock-search-btn');
  const input = document.getElementById('stock-search-input');

  if (btn && input) {
    btn.addEventListener('click', async () => {
      const ticker = input.value.trim();
      if (!ticker) return;
      const resp = await fetch(`${API_BASE}/stocks?symbol=${encodeURIComponent(ticker)}`);
      const data = await resp.json();
      alert(data.quote || 'Quote unavailable.');
    });
  }

  loadFinance();
}

async function loadFinance() {
  const container = document.getElementById('watchlist-grid');
  if (!container) return;
  try {
    const resp = await fetch(`${API_BASE}/watchlist`);
    const data = await resp.json();
    const list = data.watchlist || [];
    container.innerHTML = list.length ? list.map(item => `
      <div class="card">
        <h3>📈 ${item.symbol}</h3>
        <p style="color: var(--text-muted); margin-top: 6px;">${item.name || item.symbol}</p>
      </div>
    `).join('') : '<div class="empty-state">Watchlist is empty. Say "Track Nvidia" to add stocks.</div>';
  } catch (err) {
    console.error(err);
  }
}

// ── News ───────────────────────────────────────────────────────────────────
function initNews() {
  const buttons = document.querySelectorAll('.news-controls .filter-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadNews(btn.getAttribute('data-topic'));
    });
  });
  loadNews('world');
}

async function loadNews(topic) {
  const container = document.getElementById('news-grid');
  if (!container) return;
  container.innerHTML = '<div class="empty-state">Fetching verified RSS news...</div>';
  try {
    const resp = await fetch(`${API_BASE}/news?topic=${encodeURIComponent(topic)}`);
    const data = await resp.json();
    const lines = (data.content || '').split('\n').filter(l => l.startsWith('- '));
    container.innerHTML = lines.map(line => `
      <div class="card">
        <p style="font-size: 0.95rem; line-height: 1.4;">${line.replace('- ', '')}</p>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="empty-state">News fetch failed: ${err.message}</div>`;
  }
}

// ── Telemetry ──────────────────────────────────────────────────────────────
async function initTelemetry() {
  loadTelemetry();
  setInterval(loadTelemetry, 4000);
}

async function loadTelemetry() {
  try {
    const resp = await fetch(`${API_BASE}/status`);
    const data = await resp.json();
    const t = data.telemetry || {};
    const cpuEl = document.getElementById('cpu-stat');
    const ramEl = document.getElementById('ram-stat');
    const osEl = document.getElementById('os-stat');
    const stateEl = document.getElementById('state-stat');
    const badgeEl = document.getElementById('agent-state-label');

    if (cpuEl) cpuEl.innerText = `${t.cpu_percent || 0}%`;
    if (ramEl) ramEl.innerText = `${t.ram_percent || 0}% (${t.ram_used_gb || 0} GB)`;
    if (osEl) osEl.innerText = t.os_name || 'Windows 11';
    if (stateEl) stateEl.innerText = data.state || 'ONLINE';
    if (badgeEl) badgeEl.innerText = `DRAX ${data.state || 'ONLINE'}`;
  } catch (err) {
    console.debug('Telemetry polling fallback:', err);
  }
}
