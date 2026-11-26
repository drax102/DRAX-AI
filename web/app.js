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
  initSalesTab();
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
      if (tabId === 'sales') initSalesTab();
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

      // Async command handling: poll status if in progress
      if (data.status === 'dispatched' || data.status === 'executing') {
        const cmdId = data.command_id || data.request_id;
        const initText = 'Sending to Windows Agent...';
        const msgEl = appendMessage(initText, 'drax', {
          success: true,
          routed_to: data.routed_to || data.device_id,
          device_id: data.device_id,
        });

        if (cmdId) {
          let pollAttempts = 0;
          const maxPollAttempts = 15; // up to 12s
          const pollTimer = setInterval(async () => {
            pollAttempts++;
            try {
              const pollResp = await fetch(`${API_BASE}/commands/${encodeURIComponent(cmdId)}`, {
                headers: { 'Accept': 'application/json' }
              });
              if (pollResp.ok) {
                const pollData = await pollResp.json();
                if (pollData.status === 'success' || pollData.status === 'failed') {
                  clearInterval(pollTimer);
                  const isDoneSuccess = pollData.status === 'success';
                  const finalText = pollData.message || pollData.result || pollData.response || (isDoneSuccess ? 'Action executed successfully.' : 'Action failed on device.');
                  updateMessage(msgEl, finalText, isDoneSuccess, {
                    routed_to: pollData.device_id || 'windows_agent',
                    device_id: pollData.device_id,
                    error: pollData.error,
                  });
                }
              }
            } catch (pErr) {
              console.warn('[DRAX API] Status poll warning:', pErr);
            }
            if (pollAttempts >= maxPollAttempts) {
              clearInterval(pollTimer);
            }
          }, 800);
        }
        return;
      }

      const isSuccess = data.success !== false;
      const text = data.message || data.result || data.response || (isSuccess ? 'Executed successfully.' : 'Action failed.');

      appendMessage(text, 'drax', {
        success: isSuccess,
        routed_to: data.routed_to || data.device_id || data.source,
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

function renderMessageHtml(text, meta = null) {
  if (meta && typeof meta === 'object') {
    const isSuccess = meta.success !== false;
    const icon = isSuccess ? '✓' : '✕';
    const statusClass = isSuccess ? 'status-ok' : 'status-err';

    let html = `<div class="msg-header ${statusClass}"><strong>${icon}</strong> ${escapeHtml(text)}</div>`;

    if (meta.error) {
      const err = meta.error;
      const errReason = typeof err === 'string' ? err : (err.message || text);
      if (errReason && errReason !== text) {
        html += `<div class="msg-reason"><strong>Reason:</strong> ${escapeHtml(errReason)}</div>`;
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
    return { html, isSuccess };
  } else {
    return { html: escapeHtml(text), isSuccess: true };
  }
}

function appendMessage(text, type, meta = null) {
  const container = document.getElementById('chat-messages');
  if (!container) return null;
  const div = document.createElement('div');
  div.className = `msg ${type}`;

  const { html, isSuccess } = renderMessageHtml(text, meta);
  if (!isSuccess) div.classList.add('error-msg');
  div.innerHTML = html;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function updateMessage(div, text, isSuccess, meta = null) {
  if (!div) return;
  const { html, isSuccess: ok } = renderMessageHtml(text, { ...(meta || {}), success: isSuccess });
  if (!ok) div.classList.add('error-msg');
  else div.classList.remove('error-msg');
  div.innerHTML = html;
  const container = document.getElementById('chat-messages');
  if (container) container.scrollTop = container.scrollHeight;
}

// ── Devices Tab ────────────────────────────────────────────────────────────
async function initDevices() {
  loadDevices();
}

window.setPrimaryDevice = async function(deviceId) {
  try {
    const resp = await fetch(`${API_BASE}/api/devices/${deviceId}/primary`, { method: 'POST' });
    if (resp.ok) {
      loadDevices();
    }
  } catch (err) {
    console.error('[DRAX API] Failed to set primary device:', err);
  }
};

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
          <p style="color: var(--text-muted); font-size: 1.05rem; margin-bottom: 12px;">No connected devices currently registered.</p>
          <button class="glow-btn" onclick="document.getElementById('pair-modal-btn').click()"><i class="fa-solid fa-plus"></i> Connect A Device</button>
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

      const plat = (d.platform || 'windows').toLowerCase();
      const platIcon = plat === 'android' ? 'fa-brands fa-android' :
                       plat === 'macos' || plat === 'ios' ? 'fa-brands fa-apple' :
                       plat === 'linux' ? 'fa-brands fa-linux' :
                       plat === 'web' ? 'fa-solid fa-globe' : 'fa-brands fa-windows';

      const caps = Array.isArray(d.capabilities) ? d.capabilities : ['apps', 'media', 'system'];
      const capPillsHtml = caps.map(c => `<span class="cap-pill">${escapeHtml(c)}</span>`).join('');

      const isPrimary = d.is_primary === true;
      const primaryBadgeHtml = isPrimary
        ? `<span class="primary-badge"><i class="fa-solid fa-star"></i> Primary</span>`
        : `<button class="set-primary-btn" onclick="setPrimaryDevice('${d.device_id}')">Set Primary</button>`;

      return `
        <div class="card device-card ${isPrimary ? 'primary-device-card' : ''}">
          <div class="device-header">
            <i class="${platIcon} device-icon" style="color: ${statusColor};"></i>
            <div style="flex: 1;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3>${escapeHtml(d.name || 'Device')}</h3>
                ${primaryBadgeHtml}
              </div>
              <p style="color: ${statusColor}; margin-top: 4px;">
                <span class="status-indicator" style="background: ${statusColor};"></span>
                ${statusText} &bull; <small style="color: var(--text-muted);">${d.os_version || 'v2.0'} &bull; ${lastSeenStr}</small>
              </p>
            </div>
          </div>
          <div class="device-capabilities">
            <small style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 6px;">Advertised Capabilities</small>
            <div class="caps-container">${capPillsHtml}</div>
          </div>
          <div class="device-actions">
            <button class="device-cmd-btn" onclick="executeFromDevice('open spotify', '${d.device_id}')">Play Music</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('next song', '${d.device_id}')">Next Song</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('open chrome', '${d.device_id}')">Open Chrome</button>
            <button class="device-cmd-btn" onclick="executeFromDevice('lock pc', '${d.device_id}')">Lock Screen</button>
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

    // Async polling
    if (data.status === 'dispatched' || data.status === 'executing') {
      const cmdId = data.command_id || data.request_id;
      const initText = 'Sending to Windows Agent...';
      const msgEl = appendMessage(initText, 'drax', {
        success: true,
        routed_to: data.routed_to || deviceId,
        device_id: data.device_id || deviceId,
      });

      if (cmdId) {
        let pollAttempts = 0;
        const maxPollAttempts = 15;
        const pollTimer = setInterval(async () => {
          pollAttempts++;
          try {
            const pollResp = await fetch(`${API_BASE}/commands/${encodeURIComponent(cmdId)}`, {
              headers: { 'Accept': 'application/json' }
            });
            if (pollResp.ok) {
              const pollData = await pollResp.json();
              if (pollData.status === 'success' || pollData.status === 'failed') {
                clearInterval(pollTimer);
                const isDoneSuccess = pollData.status === 'success';
                const finalText = pollData.message || pollData.result || pollData.response || (isDoneSuccess ? 'Action executed successfully.' : 'Action failed on device.');
                updateMessage(msgEl, finalText, isDoneSuccess, {
                  routed_to: pollData.device_id || deviceId || 'windows_agent',
                  device_id: pollData.device_id || deviceId,
                  error: pollData.error,
                });
              }
            }
          } catch (pErr) {
            console.warn('[DRAX API] Status poll warning:', pErr);
          }
          if (pollAttempts >= maxPollAttempts) {
            clearInterval(pollTimer);
          }
        }, 800);
      }
      return;
    }

    const isSuccess = data.success !== false;
    const text = data.message || data.result || data.response || 'Action completed on workstation.';

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

// ══════════════════════════════════════════════════════════════════════════════
// ── AUTONOMOUS AI SALES VOICE AGENT CONTROLLER ──────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

let salesInitialized = false;
let currentSalesSessionId = null;
let isSalesVoiceEnabled = true;
let isSalesListening = false;
let isSalesProcessing = false;
let salesSpeechRecognition = null;

function initSalesTab() {
  if (salesInitialized) {
    if (currentSalesSessionId) {
      refreshSalesLead(currentSalesSessionId);
    }
    return;
  }
  salesInitialized = true;

  const inputEl = document.getElementById('sales-input');
  const sendBtn = document.getElementById('sales-send-btn');
  const micBtn = document.getElementById('sales-mic-btn');
  const voiceToggleBtn = document.getElementById('sales-voice-toggle-btn');
  const stopSpeechBtn = document.getElementById('sales-stop-speech-btn');
  const newSessionBtn = document.getElementById('sales-new-session-btn');

  // Check for existing session in sessionStorage
  const storedSession = sessionStorage.getItem('drax_sales_session_id');
  if (storedSession) {
    currentSalesSessionId = storedSession;
    updateSalesSessionUI(currentSalesSessionId);
    loadSalesHistory(currentSalesSessionId);
    refreshSalesLead(currentSalesSessionId);
  } else {
    createNewSalesSession();
  }

  // Send button listener
  if (sendBtn) {
    sendBtn.addEventListener('click', () => {
      if (inputEl) {
        const text = inputEl.value.trim();
        if (text) handleSalesSend(text);
      }
    });
  }

  // Enter key in input field
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = inputEl.value.trim();
        if (text) handleSalesSend(text);
      }
    });
  }

  // New session button
  if (newSessionBtn) {
    newSessionBtn.addEventListener('click', () => {
      createNewSalesSession();
    });
  }

  // Voice toggle (TTS) button
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener('click', () => {
      toggleSalesVoice();
    });
  }

  // Stop speech playback button
  if (stopSpeechBtn) {
    stopSpeechBtn.addEventListener('click', () => {
      stopSalesSpeech();
    });
  }

  // Browser Speech-to-Text Setup
  setupSalesSpeechRecognition(micBtn, inputEl);
}

function updateSalesVoiceStatus(statusText) {
  const statusEl = document.getElementById('sales-voice-status');
  if (statusEl) {
    statusEl.innerText = statusText;
  }
}

function updateSalesSessionUI(sessionId) {
  const labelEl = document.getElementById('sales-session-label');
  const indicatorEl = document.getElementById('sales-session-indicator');
  if (labelEl) {
    labelEl.innerText = `Session: ${sessionId}`;
  }
  if (indicatorEl) {
    indicatorEl.style.background = '#00ff88';
    indicatorEl.style.boxShadow = '0 0 8px #00ff88';
  }
}

async function createNewSalesSession() {
  stopSalesSpeech();
  if (isSalesListening && salesSpeechRecognition) {
    try { salesSpeechRecognition.stop(); } catch (_) {}
  }

  const labelEl = document.getElementById('sales-session-label');
  if (labelEl) labelEl.innerText = 'Creating session...';

  try {
    const resp = await fetch(`${API_BASE}/api/sales/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    const data = await resp.json();
    currentSalesSessionId = data.session_id;
    sessionStorage.setItem('drax_sales_session_id', currentSalesSessionId);
    updateSalesSessionUI(currentSalesSessionId);

    // Reset dialogue terminal
    const terminal = document.getElementById('sales-chat-messages');
    if (terminal) {
      terminal.innerHTML = `
        <div class="msg system">
          <i class="fa-solid fa-headset"></i> New sales consultation session initialized (<code>${currentSalesSessionId}</code>). Speak via microphone or type to begin qualification.
        </div>
      `;
    }

    // Reset Lead card
    resetLeadCardUI();
    updateSalesVoiceStatus('Ready');

    const inputEl = document.getElementById('sales-input');
    if (inputEl) {
      inputEl.value = '';
      inputEl.focus();
    }
  } catch (err) {
    console.error('[DRAX Sales] Error initializing session:', err);
    if (labelEl) labelEl.innerText = 'Session error';
    appendSalesMessage(`Failed to initialize sales session: ${err.message}. Ensure backend is running.`, 'system');
  }
}

async function loadSalesHistory(sessionId) {
  const terminal = document.getElementById('sales-chat-messages');
  if (!terminal) return;

  try {
    const resp = await fetch(`${API_BASE}/api/sales/sessions/${encodeURIComponent(sessionId)}/history`);
    if (!resp.ok) {
      if (resp.status === 404) {
        console.warn(`[DRAX Sales] Session ${sessionId} expired or not found. Creating new session.`);
        createNewSalesSession();
        return;
      }
      throw new Error(`HTTP ${resp.status}`);
    }

    const data = await resp.json();
    const turns = data.turns || [];

    terminal.innerHTML = '';
    if (turns.length === 0) {
      terminal.innerHTML = `
        <div class="msg system">
          <i class="fa-solid fa-headset"></i> Sales Voice Assistant Ready (<code>${sessionId}</code>). Speak via microphone or type to begin qualification.
        </div>
      `;
    } else {
      turns.forEach(t => {
        appendSalesMessage(t.content, t.role);
      });
      terminal.scrollTop = terminal.scrollHeight;
    }

    const turnsCountEl = document.getElementById('lead-turns-count');
    if (turnsCountEl) turnsCountEl.innerText = String(turns.length);
  } catch (err) {
    console.warn('[DRAX Sales] Error loading history:', err);
  }
}

async function refreshSalesLead(sessionId) {
  try {
    const resp = await fetch(`${API_BASE}/api/sales/sessions/${encodeURIComponent(sessionId)}/lead`);
    if (!resp.ok) return;
    const lead = await resp.json();
    updateLeadCardUI(lead);
  } catch (err) {
    console.warn('[DRAX Sales] Error refreshing lead data:', err);
  }
}

function resetLeadCardUI() {
  updateLeadCardUI({
    lead_score: 0,
    buying_intent: 'unqualified',
    qualification_status: 'in_progress',
    name: null,
    company: null,
    email: null,
    phone: null,
    role: null,
    need: null,
    budget: null,
    timeline: null,
    score_breakdown: {
      budget_score: 0,
      authority_score: 0,
      need_score: 0,
      timeline_score: 0,
      total_score: 0,
      reasoning: 'New session started. No qualification data recorded yet.'
    }
  });
  const turnsCountEl = document.getElementById('lead-turns-count');
  if (turnsCountEl) turnsCountEl.innerText = '0';
}

function updateLeadCardUI(lead) {
  if (!lead) return;

  // Lead score
  const scoreVal = lead.lead_score || 0;
  const scoreEl = document.getElementById('lead-score-val');
  if (scoreEl) {
    scoreEl.innerText = String(scoreVal);
    const box = scoreEl.closest('.score-radial-box');
    if (box) {
      if (scoreVal >= 70) {
        box.style.borderColor = 'var(--accent-green)';
        box.style.boxShadow = '0 0 16px rgba(0, 255, 136, 0.35)';
        scoreEl.style.color = 'var(--accent-green)';
      } else if (scoreVal >= 40) {
        box.style.borderColor = 'var(--accent-cyan)';
        box.style.boxShadow = '0 0 16px rgba(0, 243, 255, 0.3)';
        scoreEl.style.color = 'var(--accent-cyan)';
      } else {
        box.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        box.style.boxShadow = 'none';
        scoreEl.style.color = 'var(--text-muted)';
      }
    }
  }

  // Buying Intent
  const intentVal = lead.buying_intent || 'unqualified';
  const intentEl = document.getElementById('lead-intent-val');
  if (intentEl) {
    intentEl.innerText = intentVal.charAt(0).toUpperCase() + intentVal.slice(1);
    intentEl.className = '';
    intentEl.classList.add(`intent-${intentVal.toLowerCase()}`);
  }

  // Qualification Status & Badge
  const statusVal = lead.qualification_status || 'in_progress';
  const statusEl = document.getElementById('lead-status-val');
  if (statusEl) {
    statusEl.innerText = statusVal;
  }

  const badgeEl = document.getElementById('sales-qual-badge');
  if (badgeEl) {
    badgeEl.innerText = statusVal.toUpperCase().replace(/_/g, ' ');
    badgeEl.className = '';
    if (statusVal === 'qualified') {
      badgeEl.classList.add('qual-badge-qualified');
    } else if (statusVal === 'disqualified') {
      badgeEl.classList.add('qual-badge-disqualified');
    } else if (statusVal === 'follow_up') {
      badgeEl.classList.add('qual-badge-followup');
    } else {
      badgeEl.classList.add('qual-badge-inprogress');
    }
  }

  // BANT Breakdown
  const b = lead.score_breakdown || {};
  const budget = b.budget_score || 0;
  const authority = b.authority_score || 0;
  const need = b.need_score || 0;
  const timeline = b.timeline_score || 0;

  const budgetScoreEl = document.getElementById('bant-budget-score');
  const budgetFillEl = document.getElementById('bant-budget-fill');
  if (budgetScoreEl) budgetScoreEl.innerText = `${budget} / 25`;
  if (budgetFillEl) budgetFillEl.style.width = `${Math.min(100, (budget / 25) * 100)}%`;

  const authScoreEl = document.getElementById('bant-authority-score');
  const authFillEl = document.getElementById('bant-authority-fill');
  if (authScoreEl) authScoreEl.innerText = `${authority} / 25`;
  if (authFillEl) authFillEl.style.width = `${Math.min(100, (authority / 25) * 100)}%`;

  const needScoreEl = document.getElementById('bant-need-score');
  const needFillEl = document.getElementById('bant-need-fill');
  if (needScoreEl) needScoreEl.innerText = `${need} / 25`;
  if (needFillEl) needFillEl.style.width = `${Math.min(100, (need / 25) * 100)}%`;

  const timeScoreEl = document.getElementById('bant-timeline-score');
  const timeFillEl = document.getElementById('bant-timeline-fill');
  if (timeScoreEl) timeScoreEl.innerText = `${timeline} / 25`;
  if (timeFillEl) timeFillEl.style.width = `${Math.min(100, (timeline / 25) * 100)}%`;

  // Customer Details Table
  const setDetail = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.innerText = val ? String(val) : 'Not provided';
  };
  setDetail('lead-field-name', lead.name);
  setDetail('lead-field-company', lead.company);
  setDetail('lead-field-email', lead.email);
  setDetail('lead-field-phone', lead.phone);
  setDetail('lead-field-role', lead.role);
  setDetail('lead-field-need', lead.need);
  setDetail('lead-field-budget', lead.budget);
  setDetail('lead-field-timeline', lead.timeline);

  // Score Explanation / Reasoning
  const reasonEl = document.getElementById('lead-reasoning-text');
  if (reasonEl) {
    reasonEl.innerText = b.reasoning || (scoreVal > 0 ? 'Lead evaluated against BANT framework.' : 'No evaluation criteria recorded yet.');
  }
}

function appendSalesMessage(text, role) {
  const terminal = document.getElementById('sales-chat-messages');
  if (!terminal) return;

  const msgDiv = document.createElement('div');
  const isUser = role === 'user';
  const isSys = role === 'system';

  msgDiv.className = `msg ${isUser ? 'user' : isSys ? 'system' : 'drax'}`;

  const headerDiv = document.createElement('div');
  headerDiv.style.fontSize = '0.75rem';
  headerDiv.style.marginBottom = '4px';

  if (isUser) {
    headerDiv.style.color = 'rgba(0, 243, 255, 0.7)';
    headerDiv.style.textAlign = 'right';
    headerDiv.innerHTML = '<i class="fa-solid fa-user"></i> Prospect / Client';
  } else if (isSys) {
    headerDiv.style.color = 'var(--text-muted)';
    headerDiv.innerHTML = '<i class="fa-solid fa-circle-info"></i> System';
  } else {
    headerDiv.style.color = 'var(--accent-green)';
    headerDiv.innerHTML = '<i class="fa-solid fa-headset"></i> DRAX Sales Voice Agent';
  }

  const textSpan = document.createElement('div');
  textSpan.style.whiteSpace = 'pre-wrap';
  textSpan.style.wordBreak = 'break-word';
  textSpan.textContent = text;

  msgDiv.appendChild(headerDiv);
  msgDiv.appendChild(textSpan);
  terminal.appendChild(msgDiv);
  terminal.scrollTop = terminal.scrollHeight;
}

function showSalesLoading() {
  const terminal = document.getElementById('sales-chat-messages');
  if (!terminal) return null;

  const div = document.createElement('div');
  div.className = 'msg drax loading-msg';
  div.id = 'sales-loading-bubble';
  div.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Consulting sales agent...';
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
  return div;
}

function removeSalesLoading() {
  const el = document.getElementById('sales-loading-bubble');
  if (el && el.parentNode) {
    el.parentNode.removeChild(el);
  }
}

async function handleSalesSend(rawText) {
  const text = (rawText || '').trim();
  if (!text || isSalesProcessing) return;

  // Stop any active speech recognition to avoid duplicate trailing events
  if (isSalesListening && salesSpeechRecognition) {
    try { salesSpeechRecognition.stop(); } catch (_) {}
  }

  // Ensure active session
  if (!currentSalesSessionId) {
    await createNewSalesSession();
    if (!currentSalesSessionId) return;
  }

  isSalesProcessing = true;
  const inputEl = document.getElementById('sales-input');
  const sendBtn = document.getElementById('sales-send-btn');
  const micBtn = document.getElementById('sales-mic-btn');

  if (inputEl) {
    inputEl.value = '';
    inputEl.disabled = true;
  }
  if (sendBtn) sendBtn.disabled = true;
  if (micBtn) micBtn.disabled = true;

  // Append user's message
  appendSalesMessage(text, 'user');
  showSalesLoading();
  updateSalesVoiceStatus('Processing...');

  try {
    const resp = await fetch(`${API_BASE}/api/sales/sessions/${encodeURIComponent(currentSalesSessionId)}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ message: text })
    });

    removeSalesLoading();

    if (!resp.ok) {
      if (resp.status === 404) {
        appendSalesMessage('Sales session expired. Starting a fresh consultation session...', 'system');
        await createNewSalesSession();
        return;
      }
      let errDetail = `Server error (HTTP ${resp.status})`;
      try {
        const errJson = await resp.json();
        if (errJson.detail) errDetail = errJson.detail;
      } catch (_) {}
      appendSalesMessage(`Agent Error: ${errDetail}`, 'system');
      updateSalesVoiceStatus('Error');
      return;
    }

    const data = await resp.json();

    // Render agent dialogue
    appendSalesMessage(data.response, 'assistant');

    // Update engine badge
    const modelBadge = document.getElementById('sales-model-badge');
    if (modelBadge) {
      if (data.is_demo) {
        modelBadge.innerText = 'DEMO ENGINE';
        modelBadge.className = 'badge-demo';
      } else {
        modelBadge.innerText = (data.model_used || 'AI ENGINE').toUpperCase();
        modelBadge.className = 'badge-live';
      }
    }

    // Update turns logged
    const turnsCountEl = document.getElementById('lead-turns-count');
    if (turnsCountEl) {
      turnsCountEl.innerText = String(data.history_length || 0);
    }

    // Refresh lead scores and qualification card
    await refreshSalesLead(currentSalesSessionId);

    // Speak AI voice if enabled
    if (isSalesVoiceEnabled) {
      speakSalesUtterance(data.response);
    } else {
      updateSalesVoiceStatus('Ready');
    }

  } catch (netErr) {
    removeSalesLoading();
    console.error('[DRAX Sales] Network error:', netErr);
    appendSalesMessage(`Network Error: ${netErr.message}. Ensure backend is reachable.`, 'system');
    updateSalesVoiceStatus('Error');
  } finally {
    isSalesProcessing = false;
    if (inputEl) {
      inputEl.disabled = false;
      inputEl.focus();
    }
    if (sendBtn) sendBtn.disabled = false;
    if (micBtn) micBtn.disabled = false;
  }
}

// ── Voice Output (TTS via SpeechSynthesis) ───────────────────────────────────
function cleanTextForSpeech(text) {
  if (!text) return '';
  return text
    .replace(/[*#_`~]/g, '')
    .replace(/https?:\/\/\S+/g, 'link')
    .replace(/\s+/g, ' ')
    .trim();
}

function speakSalesUtterance(text) {
  if (!('speechSynthesis' in window)) {
    console.warn('[DRAX Sales] Browser does not support SpeechSynthesis.');
    updateSalesVoiceStatus('Ready (TTS unsupported)');
    return;
  }

  // Stop any active speech
  window.speechSynthesis.cancel();

  const clean = cleanTextForSpeech(text);
  if (!clean) {
    updateSalesVoiceStatus('Ready');
    return;
  }

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  // Select preferred natural English voice if available
  const voices = window.speechSynthesis.getVoices();
  if (voices && voices.length > 0) {
    const preferredVoice = voices.find(v =>
      (v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Samantha') || v.name.includes('Zira') || v.name.includes('David')))
    ) || voices.find(v => v.lang.startsWith('en'));
    if (preferredVoice) utterance.voice = preferredVoice;
  }

  utterance.onstart = () => {
    updateSalesVoiceStatus('Speaking...');
  };

  utterance.onend = () => {
    updateSalesVoiceStatus('Ready');
  };

  utterance.onerror = (e) => {
    console.warn('[DRAX Sales] SpeechSynthesis playback error:', e);
    updateSalesVoiceStatus('Ready');
  };

  window.speechSynthesis.speak(utterance);
}

function stopSalesSpeech() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  updateSalesVoiceStatus('Ready');
}

function toggleSalesVoice() {
  isSalesVoiceEnabled = !isSalesVoiceEnabled;
  const toggleBtn = document.getElementById('sales-voice-toggle-btn');
  const iconEl = document.getElementById('sales-voice-icon');
  const labelEl = document.getElementById('sales-voice-label');

  if (isSalesVoiceEnabled) {
    if (toggleBtn) toggleBtn.classList.remove('voice-off');
    if (iconEl) iconEl.className = 'fa-solid fa-volume-high';
    if (labelEl) labelEl.innerText = 'Voice On';
  } else {
    stopSalesSpeech();
    if (toggleBtn) toggleBtn.classList.add('voice-off');
    if (iconEl) iconEl.className = 'fa-solid fa-volume-xmark';
    if (labelEl) labelEl.innerText = 'Voice Off';
  }
}

// ── Voice Input (STT via Web Speech API) ─────────────────────────────────────
function setupSalesSpeechRecognition(micBtn, inputEl) {
  if (!micBtn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    console.warn('[DRAX Sales] Web Speech Recognition is not supported by this browser.');
    micBtn.title = 'Speech recognition not supported in this browser (Use text input)';
    micBtn.addEventListener('click', () => {
      alert('Speech recognition is not supported in this browser.\nPlease use Google Chrome, Microsoft Edge, or Safari, or use keyboard text input.');
    });
    return;
  }

  try {
    salesSpeechRecognition = new SpeechRecognition();
    salesSpeechRecognition.continuous = false;
    salesSpeechRecognition.interimResults = true;
    salesSpeechRecognition.lang = 'en-US';

    let speechSubmitted = false;

    salesSpeechRecognition.onstart = () => {
      isSalesListening = true;
      speechSubmitted = false;
      micBtn.classList.add('mic-active');
      updateSalesVoiceStatus('Listening...');
    };

    salesSpeechRecognition.onresult = (event) => {
      if (isSalesProcessing || speechSubmitted) return;

      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (inputEl) {
        inputEl.value = finalTranscript || interimTranscript;
      }

      // If a final speech turn is captured, auto-submit exactly once
      if (finalTranscript.trim() && !speechSubmitted) {
        speechSubmitted = true;
        try { salesSpeechRecognition.stop(); } catch (_) {}
        handleSalesSend(finalTranscript.trim());
      }
    };

    salesSpeechRecognition.onerror = (event) => {
      isSalesListening = false;
      micBtn.classList.remove('mic-active');
      console.warn('[DRAX Sales] Speech recognition error:', event.error);

      if (event.error === 'not-allowed') {
        alert('Microphone access was denied. Please allow microphone permissions in your browser to use voice input.');
      }
      updateSalesVoiceStatus('Ready');
    };

    salesSpeechRecognition.onend = () => {
      isSalesListening = false;
      micBtn.classList.remove('mic-active');
      const statusEl = document.getElementById('sales-voice-status');
      if (statusEl && statusEl.innerText === 'Listening...') {
        updateSalesVoiceStatus('Ready');
      }
    };

    micBtn.addEventListener('click', () => {
      if (isSalesProcessing) return;

      if (isSalesListening) {
        try { salesSpeechRecognition.stop(); } catch (_) {}
      } else {
        stopSalesSpeech();
        try {
          salesSpeechRecognition.start();
        } catch (err) {
          console.warn('[DRAX Sales] Speech start error:', err);
        }
      }
    });

  } catch (initErr) {
    console.error('[DRAX Sales] Failed to initialize SpeechRecognition:', initErr);
  }
}
