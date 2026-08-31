// Drax AI Web Dashboard Controller (Production & Cloud Ready)

// Dynamic API URL Resolution (Priority: URL query ?api= -> localStorage -> window.DRAX_API_URL -> localhost -> default Render Cloud backend)
function getApiBase() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramApi = urlParams.get('api');
  if (paramApi) {
    const clean = paramApi.replace(/\/$/, '');
    localStorage.setItem('drax_api_url', clean);
    return clean;
  }

  const stored = localStorage.getItem('drax_api_url');
  if (stored) {
    const clean = stored.replace(/\/$/, '');
    if (window.location.protocol === 'https:') {
      if (clean.startsWith('https://')) return clean;
      localStorage.removeItem('drax_api_url');
    } else {
      return clean;
    }
  }

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

  function openPairModal() {
    if (pairModal) {
      pairModal.classList.add('active');
      if (pairingInput) {
        pairingInput.value = '';
        pairingInput.focus();
      }
    }
  }

  if (openPairBtn) openPairBtn.addEventListener('click', openPairModal);
  if (openPairBtn2) openPairBtn2.addEventListener('click', openPairModal);
  if (cancelPairBtn) cancelPairBtn.addEventListener('click', () => pairModal.classList.remove('active'));

  if (submitPairBtn) {
    submitPairBtn.addEventListener('click', async () => {
      const code = pairingInput ? pairingInput.value.trim().toUpperCase() : '';
      if (!code) {
        alert('Please enter your 4-character pairing code (e.g. DRAX-7K92).');
        return;
      }
      submitPairBtn.innerText = 'Connecting...';
      submitPairBtn.disabled = true;
      try {
        console.log('[DRAX API] Submitting pairing code:', code);
        const resp = await fetch(`${API_BASE}/api/pair/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pairing_code: code })
        });
        if (resp.ok) {
          const res = await resp.json();
          const dev = res.device || {};
          alert(`✓ PC Connected!\nDevice: ${dev.name || 'Windows Workstation'}\nPlatform: ${dev.platform || 'Windows'}\nAgent: Online & Listening`);
          pairModal.classList.remove('active');
          loadDevices();
          loadTelemetry();
        } else {
          const err = await resp.json();
          alert(`Pairing failed: ${err.detail || 'Invalid or expired pairing code.'}`);
        }
      } catch (e) {
        console.error('[DRAX API] Pairing network error:', e);
        alert(`Error contacting cloud API: ${e.message}`);
      } finally {
        submitPairBtn.innerText = 'Connect Device';
        submitPairBtn.disabled = false;
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

function escapeHtml(unsafe) {
  if (typeof unsafe !== 'string') return String(unsafe || '');
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showLoading(cmd) {
  const container = document.getElementById('chat-messages');
  if (!container) return null;
  const div = document.createElement('div');
  div.className = 'msg drax loading-msg';
  div.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> DRAX is working on <em>"${escapeHtml(cmd)}"</em>...`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function removeLoading(el) {
  if (el && el.parentNode) {
    el.parentNode.removeChild(el);
  }
}

// ── Chat & Command Terminal ────────────────────────────────────────────────
function initChat() {
  const input = document.getElementById('command-input');
  const sendBtn = document.getElementById('send-btn');
  const voiceBtn = document.getElementById('voice-btn');
  const quickBrief = document.getElementById('quick-brief-btn');

  let isExecuting = false;

  async function execute(cmd) {
    if (!cmd || !cmd.trim() || isExecuting) return;
    isExecuting = true;
    if (sendBtn) sendBtn.disabled = true;
    if (input) input.value = '';

    appendMessage(cmd, 'user');
    const loader = showLoading(cmd);

    try {
      console.log('[DRAX API] Executing command:', cmd, '-> Endpoint:', `${API_BASE}/command`);
      const resp = await fetch(`${API_BASE}/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ command: cmd })
      });

      removeLoading(loader);

      if (!resp.ok) {
        let errTitle = `HTTP ${resp.status} Error`;
        let errMessage = `Server returned status ${resp.status} (${resp.statusText})`;
        let errDetails = '';

        if (resp.status === 503) {
          errTitle = 'Windows Agent Offline';
          errMessage = 'No paired Windows Agent is currently connected online.';
          errDetails = 'Start Drax AI on your Windows workstation and verify the WebSocket connection.';
        } else if (resp.status === 504 || resp.status === 408) {
          errTitle = 'Command Timed Out';
          errMessage = 'Windows Agent or cloud service did not respond in time.';
          errDetails = 'The request exceeded the execution deadline.';
        } else if (resp.status === 500) {
          errTitle = 'Cloud Internal Error';
          errMessage = 'DRAX Cloud API encountered an internal server error.';
        } else if (resp.status === 404) {
          errTitle = 'Resource Not Found';
          errMessage = 'Requested API endpoint or device was not found.';
        }

        try {
          const errData = await resp.json();
          if (errData.detail) errMessage = errData.detail;
          else if (errData.message) errMessage = errData.message;
          if (errData.error) {
            errMessage = errData.error.message || errMessage;
            errDetails = errData.error.details || errDetails;
          }
        } catch (_) {
          try {
            const txt = await resp.text();
            if (txt) errDetails = txt;
          } catch (_) {}
        }

        console.warn('[DRAX API] Command execution returned HTTP error:', resp.status, errMessage);
        appendMessage(errTitle, 'drax', {
          success: false,
          error: {
            code: `HTTP_${resp.status}`,
            layer: resp.status === 503 ? 'WINDOWS AGENT' : 'CLOUD',
            message: errMessage,
            details: errDetails
          }
        });
        return;
      }

      let data;
      try {
        data = await resp.json();
      } catch (jsonErr) {
        console.error('[DRAX API] Invalid JSON response:', jsonErr);
        appendMessage('Invalid Cloud Response', 'drax', {
          success: false,
          error: {
            code: 'INVALID_JSON',
            layer: 'CLOUD',
            message: 'Received invalid JSON payload from DRAX Cloud API.',
            details: String(jsonErr)
          }
        });
        return;
      }

      console.log('[DRAX API] Response received:', data);
      const isSuccess = data.success !== false;
      const text = data.response || data.result || data.message || 'Executed successfully.';

      appendMessage(text, 'drax', {
        success: isSuccess,
        routed_to: data.routed_to,
        device_id: data.device_id,
        error: data.error
      });

    } catch (err) {
      removeLoading(loader);
      console.error('[DRAX API] Command connection error:', err);

      let isNetwork = err.name === 'TypeError' || String(err.message).includes('Failed to fetch');
      let errMsg = isNetwork
        ? 'Unable to reach DRAX Cloud. Check your internet connection or Render backend service.'
        : `Connection error: ${err.message}`;

      appendMessage(isNetwork ? 'Network Connection Error' : 'Client Error', 'drax', {
        success: false,
        error: {
          code: isNetwork ? 'NETWORK_UNREACHABLE' : 'CLIENT_EXCEPTION',
          layer: 'BROWSER',
          message: errMsg,
          details: `API Endpoint: ${API_BASE}/command | ${String(err)}`
        }
      });
    } finally {
      removeLoading(loader);
      isExecuting = false;
      if (sendBtn) sendBtn.disabled = false;
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

function appendMessage(text, type, meta = null) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `msg ${type}`;

  if (meta && typeof meta === 'object') {
    const isSuccess = meta.success !== false;
    const icon = isSuccess ? '✓' : '✕';
    const statusClass = isSuccess ? 'status-ok' : 'status-err';
    if (!isSuccess) div.classList.add('error-msg');

    let html = `<div class="msg-header ${statusClass}"><strong>${icon}</strong> ${escapeHtml(text)}</div>`;

    if (meta.error) {
      const err = meta.error;
      if (err.message && err.message !== text) {
        html += `<div class="msg-reason"><strong>Reason:</strong> ${escapeHtml(err.message)}</div>`;
      }

      const detailId = `detail_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
      html += `
        <div class="msg-details-toggle" onclick="document.getElementById('${detailId}').classList.toggle('active')">
          <small><i class="fa-solid fa-circle-info"></i> [Show details]</small>
        </div>
        <div class="msg-details-content" id="${detailId}">
          <div><strong>Layer:</strong> ${escapeHtml(err.layer || meta.routed_to || 'SYSTEM')}</div>
          <div><strong>Code:</strong> ${escapeHtml(err.code || 'ERROR')}</div>
          ${meta.device_id ? `<div><strong>Device:</strong> ${escapeHtml(meta.device_id)}</div>` : ''}
          ${err.details ? `<div><strong>Details:</strong> ${escapeHtml(err.details)}</div>` : ''}
        </div>
      `;
    }
    div.innerHTML = html;
  } else {
    div.innerText = text;
  }

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
    if (!resp.ok) return;
    const data = await resp.json();
    const devices = data.devices || [];

    if (devices.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1; padding: 30px; text-align: center;">
          <p style="color: var(--text-muted); font-size: 1.05rem; margin-bottom: 12px;">No paired Windows Agent is currently registered.</p>
          <button class="glow-btn" onclick="document.getElementById('pair-modal-btn').click()"><i class="fa-solid fa-plus"></i> Pair Your Windows PC</button>
        </div>
      `;
      return;
    }

    const now = Date.now() / 1000;
    container.innerHTML = devices.map(d => {
      const isOnline = d.status === 'online' || d.online === true;
      const statusColor = isOnline ? '#00ff88' : '#8b949e';
      const statusText = isOnline ? 'Online & Listening' : 'Offline';
      const lastSeenSecs = Math.max(0, Math.floor(now - (d.last_seen || 0)));
      const lastSeenStr = lastSeenSecs < 10 ? 'Just now' : lastSeenSecs < 60 ? `${lastSeenSecs}s ago` : `${Math.floor(lastSeenSecs / 60)}m ago`;

      return `
        <div class="card device-card">
          <div class="device-header">
            <i class="fa-brands fa-windows device-icon" style="color: ${statusColor};"></i>
            <div>
              <h3>${escapeHtml(d.name || 'Windows PC')}</h3>
              <p style="color: ${statusColor}; margin-top: 4px;">
                <span class="status-indicator" style="background: ${statusColor};"></span>
                ${statusText} &bull; <small style="color: var(--text-muted);">${lastSeenStr}</small>
              </p>
            </div>
          </div>
          <div class="device-actions">
            <button class="device-cmd-btn" onclick="executeFromDevice('open spotify', '${d.device_id}')">Open Spotify</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('open chrome', '${d.device_id}')">Open Chrome</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('lock pc', '${d.device_id}')">Lock PC</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('take screenshot', '${d.device_id}')">Screenshot</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('[DRAX API] Failed to load devices:', err);
  }
}

let isDeviceExecuting = false;

window.executeFromDevice = async function(cmd, deviceId = null) {
  if (!cmd || !cmd.trim() || isDeviceExecuting) return;
  isDeviceExecuting = true;

  appendMessage(cmd, 'user');
  const chatBtn = document.querySelector('[data-tab="chat"]');
  if (chatBtn) chatBtn.click();

  const loader = showLoading(cmd);

  try {
    console.log('[DRAX API] Dispatching command for device:', deviceId, 'cmd:', cmd);
    const resp = await fetch(`${API_BASE}/command`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ command: cmd, device_id: deviceId })
    });

    removeLoading(loader);

    if (!resp.ok) {
      let errTitle = `HTTP ${resp.status} Error`;
      let errMessage = `Server returned status ${resp.status}`;
      let errDetails = '';

      if (resp.status === 503) {
        errTitle = 'Windows Agent Offline';
        errMessage = 'Selected Windows Agent is offline.';
      } else if (resp.status === 504 || resp.status === 408) {
        errTitle = 'Command Timed Out';
        errMessage = 'Windows Agent did not respond in time.';
      }

      try {
        const errJson = await resp.json();
        if (errJson.detail) errMessage = errJson.detail;
        else if (errJson.message) errMessage = errJson.message;
        if (errJson.error) {
          errMessage = errJson.error.message || errMessage;
          errDetails = errJson.error.details || errDetails;
        }
      } catch (_) {
        try {
          const txt = await resp.text();
          if (txt) errDetails = txt;
        } catch (_) {}
      }

      appendMessage(errTitle, 'drax', {
        success: false,
        error: {
          code: `HTTP_${resp.status}`,
          layer: resp.status === 503 ? 'WINDOWS AGENT' : 'CLOUD',
          message: errMessage,
          details: errDetails
        }
      });
      return;
    }

    let data;
    try {
      data = await resp.json();
    } catch (jsonErr) {
      appendMessage('Invalid Cloud Response', 'drax', {
        success: false,
        error: {
          code: 'INVALID_JSON',
          layer: 'CLOUD',
          message: 'Received invalid JSON payload from DRAX Cloud API.',
          details: String(jsonErr)
        }
      });
      return;
    }

    console.log('[DRAX API] Device command response:', data);
    const isSuccess = data.success !== false;
    const text = data.response || data.result || data.message || 'Action completed on workstation.';

    appendMessage(text, 'drax', {
      success: isSuccess,
      routed_to: data.routed_to || deviceId,
      device_id: data.device_id || deviceId,
      error: data.error
    });

  } catch (e) {
    removeLoading(loader);
    console.error('[DRAX API] Device dispatch error:', e);
    let isNetwork = e.name === 'TypeError' || String(e.message).includes('Failed to fetch');
    let errMsg = isNetwork
      ? 'Unable to reach DRAX Cloud. Check your internet connection or Render backend service.'
      : `Device dispatch failed: ${e.message}`;

    appendMessage(isNetwork ? 'Network Connection Error' : 'Dispatch Error', 'drax', {
      success: false,
      error: {
        code: isNetwork ? 'NETWORK_UNREACHABLE' : 'CLIENT_EXCEPTION',
        layer: 'BROWSER',
        message: errMsg,
        details: `API Endpoint: ${API_BASE}/command | ${String(e)}`
      }
    });
  } finally {
    removeLoading(loader);
    isDeviceExecuting = false;
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
      try {
        const resp = await fetch(`${API_BASE}/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: title })
        });
        if (!resp.ok) {
          console.warn('[DRAX API] Failed to add task:', resp.status);
        }
      } catch (err) {
        console.error('[DRAX API] Add task network error:', err);
      }
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
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
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
    console.error('[DRAX API] Tasks fetch error:', err);
    container.innerHTML = `<div class="empty-state">Failed to load tasks (${err.message}).</div>`;
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
    if (remResp.ok) {
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
    } else {
      console.warn('[DRAX API] Failed to fetch reminders:', remResp.status);
    }

    const alarmResp = await fetch(`${API_BASE}/alarms`);
    if (alarmResp.ok) {
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
    } else {
      console.warn('[DRAX API] Failed to fetch alarms:', alarmResp.status);
    }
  } catch (err) {
    console.error('[DRAX API] Reminders/alarms fetch error:', err);
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
      try {
        const resp = await fetch(`${API_BASE}/stocks?symbol=${encodeURIComponent(ticker)}`);
        const data = await resp.json();
        alert(data.quote || 'Quote unavailable.');
      } catch (err) {
        console.error('[DRAX API] Stock search error:', err);
        alert(`Failed to fetch stock quote: ${err.message}`);
      }
    });
  }

  loadFinance();
}

async function loadFinance() {
  const container = document.getElementById('watchlist-grid');
  if (!container) return;
  try {
    const resp = await fetch(`${API_BASE}/watchlist`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const data = await resp.json();
    const list = data.watchlist || [];
    container.innerHTML = list.length ? list.map(item => `
      <div class="card">
        <h3>📈 ${item.symbol}</h3>
        <p style="color: var(--text-muted); margin-top: 6px;">${item.name || item.symbol}</p>
      </div>
    `).join('') : '<div class="empty-state">Watchlist is empty. Say "Track Nvidia" to add stocks.</div>';
  } catch (err) {
    console.error('[DRAX API] Watchlist fetch error:', err);
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
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const data = await resp.json();
    const lines = (data.content || '').split('\n').filter(l => l.startsWith('- '));
    container.innerHTML = lines.map(line => `
      <div class="card">
        <p style="font-size: 0.95rem; line-height: 1.4;">${line.replace('- ', '')}</p>
      </div>
    `).join('');
  } catch (err) {
    console.error('[DRAX API] News fetch error:', err);
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
    if (!resp.ok) return;
    const data = await resp.json();
    const t = data.telemetry || {};
    const cpuEl = document.getElementById('cpu-stat');
    const ramEl = document.getElementById('ram-stat');
    const osEl = document.getElementById('os-stat');
    const stateEl = document.getElementById('state-stat');
    const badgeEl = document.getElementById('agent-state-label');
    const indicatorEl = document.getElementById('status-indicator');

    const hasOnlinePC = (data.connected_devices > 0) || (data.devices && data.devices.some(d => d.status === 'online' || d.online === true));

    if (cpuEl) cpuEl.innerText = `${t.cpu_percent || t.cpu_usage || 0}%`;
    if (ramEl) ramEl.innerText = `${t.ram_percent || t.ram_usage || 0}% (${t.ram_used_gb || t.ram_formatted || 0})`;
    if (osEl) osEl.innerText = t.os_name || 'Windows 11';
    if (stateEl) stateEl.innerText = hasOnlinePC ? 'ONLINE & LISTENING' : 'STANDBY (NO PC)';

    if (badgeEl) {
      if (hasOnlinePC) {
        const firstOnline = (data.devices || []).find(d => d.status === 'online' || d.online === true);
        const devName = firstOnline ? (firstOnline.name || firstOnline.device_id) : 'Windows PC';
        badgeEl.innerHTML = `● DRAX CLOUD ONLINE<br><span style="font-size: 0.72rem; color: #00ff88; font-weight: normal;">● AGENT: ${devName}</span>`;
        if (indicatorEl) {
          indicatorEl.style.background = '#00ff88';
          indicatorEl.style.boxShadow = '0 0 8px #00ff88';
        }
      } else {
        badgeEl.innerHTML = `● DRAX CLOUD ONLINE<br><span style="font-size: 0.72rem; color: #8b949e; font-weight: normal;">○ AGENT OFFLINE</span>`;
        if (indicatorEl) {
          indicatorEl.style.background = '#ffaa00';
          indicatorEl.style.boxShadow = 'none';
        }
      }
    }
  } catch (err) {
    console.debug('[DRAX API] Telemetry polling fallback:', err);
  }
}
