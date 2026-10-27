/**
 * NetWatcher Web - Frontend Application Logic
 * Real-time monitoring, Canvas live chart, Web Audio alerts, and device management.
 */

// Application State
const state = {
  devices: [],
  networkStats: null,
  scanStatus: { is_scanning: false },
  soundAlerts: localStorage.getItem('netwatcher_sound') !== 'false',
  activeFilter: 'all',
  searchQuery: '',
  bandwidthHistory: {
    download: Array(45).fill(0),
    upload: Array(45).fill(0)
  },
  knownMacs: new Set()
};

// Web Audio Chime Generator
class SoundManager {
  constructor() {
    this.ctx = null;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playDeviceJoined() {
    if (!state.soundAlerts) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc1 = this.ctx.createOscillator();
    const osc2 = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(587.33, now); // D5
    osc1.frequency.exponentialRampToValueAtTime(880.00, now + 0.15); // A5

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc1.connect(gain);
    gain.connect(this.ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.35);
  }

  playDeviceLeft() {
    if (!state.soundAlerts) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(440.00, now); // A4
    osc.frequency.exponentialRampToValueAtTime(293.66, now + 0.25); // D4

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + 0.3);
  }
}

const sounds = new SoundManager();

// DOM Elements
const elements = {
  statOnlineCount: document.getElementById('statOnlineCount'),
  statTotalCount: document.getElementById('statTotalCount'),
  statDownSpeed: document.getElementById('statDownSpeed'),
  statDownTotal: document.getElementById('statDownTotal'),
  statUpSpeed: document.getElementById('statUpSpeed'),
  statUpTotal: document.getElementById('statUpTotal'),
  statWifiSignal: document.getElementById('statWifiSignal'),
  statWifiMeta: document.getElementById('statWifiMeta'),
  
  devicesTableBody: document.getElementById('devicesTableBody'),
  scanProgressBar: document.getElementById('scanProgressBar'),
  scanProgressWrapper: document.getElementById('scanProgressWrapper'),
  scanPercentText: document.getElementById('scanPercentText'),
  scanStatusText: document.getElementById('scanStatusText'),
  btnScanNow: document.getElementById('btnScanNow'),
  
  searchInput: document.getElementById('searchInput'),
  filterPills: document.querySelectorAll('.filter-pill'),
  tabButtons: document.querySelectorAll('.tab-btn'),
  tabPanes: document.querySelectorAll('.tab-pane'),
  soundToggle: document.getElementById('soundToggle'),
  autoScanSelect: document.getElementById('autoScanSelect'),
  
  // Param items
  paramLocalIp: document.getElementById('paramLocalIp'),
  paramActiveIface: document.getElementById('paramActiveIface'),
  paramSubnet: document.getElementById('paramSubnet'),
  paramGateway: document.getElementById('paramGateway'),
  paramDns: document.getElementById('paramDns'),
  paramMac: document.getElementById('paramMac'),
  paramSsid: document.getElementById('paramSsid'),
  paramRadioType: document.getElementById('paramRadioType'),
  paramBandChannel: document.getElementById('paramBandChannel'),
  paramLinkSpeed: document.getElementById('paramLinkSpeed'),
  paramBssid: document.getElementById('paramBssid'),
  adaptersList: document.getElementById('adaptersList'),

  // Tools
  pingInput: document.getElementById('pingInput'),
  btnRunPing: document.getElementById('btnRunPing'),
  pingOutput: document.getElementById('pingOutput'),
  portScanInput: document.getElementById('portScanInput'),
  btnRunPortScan: document.getElementById('btnRunPortScan'),
  portScanOutput: document.getElementById('portScanOutput'),

  // Modal
  aliasModal: document.getElementById('aliasModal'),
  aliasMacInput: document.getElementById('aliasMacInput'),
  aliasNameInput: document.getElementById('aliasNameInput'),
  aliasTargetDesc: document.getElementById('aliasTargetDesc'),
  btnSaveAlias: document.getElementById('btnSaveAlias'),
  btnCancelAlias: document.getElementById('btnCancelAlias'),
  modalCloseBtn: document.getElementById('modalCloseBtn'),

  toastContainer: document.getElementById('toastContainer')
};

// Toast Notifications
function showToast(message, type = 'info', title = '') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div>
      ${title ? `<div style="font-weight:700; font-size:0.85rem; margin-bottom:2px;">${title}</div>` : ''}
      <div style="font-size:0.82rem; color:#e5e7eb;">${message}</div>
    </div>
    <button style="background:none; border:none; color:#9ca3af; cursor:pointer; margin-left:8px;" onclick="this.parentElement.remove()">✕</button>
  `;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 4500);
}

// Copy to Clipboard
function copyToClipboard(text, label = 'Nội dung') {
  navigator.clipboard.writeText(text).then(() => {
    showToast(`Đã sao chép ${label}: ${text}`, 'success');
  }).catch(() => {
    showToast(`Không thể sao chép`, 'warning');
  });
}

// Tabs Navigation
elements.tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    elements.tabButtons.forEach(b => b.classList.remove('active'));
    elements.tabPanes.forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    
    const targetPane = document.getElementById(`tab-${target}`);
    if (targetPane) targetPane.classList.add('active');

    // If switching to parameters tab, immediately resize canvas and draw
    if (target === 'parameters') {
      setTimeout(() => {
        resizeCanvas();
        drawBandwidthChart();
      }, 50);
    }
  });
});

// Sound Toggle
if (elements.soundToggle) {
  elements.soundToggle.checked = state.soundAlerts;
  elements.soundToggle.addEventListener('change', (e) => {
    state.soundAlerts = e.target.checked;
    localStorage.setItem('netwatcher_sound', state.soundAlerts);
    sounds.init();
    if (state.soundAlerts) sounds.playDeviceJoined();
  });
}

// Canvas Bandwidth Chart
const canvas = document.getElementById('bandwidthChart');
const ctx = canvas ? canvas.getContext('2d') : null;

function resizeCanvas() {
  if (!canvas) return;
  const parentWidth = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
  if (parentWidth > 0) {
    canvas.width = parentWidth;
  } else {
    const container = document.querySelector('.app-container');
    canvas.width = container ? Math.max(300, container.clientWidth - 50) : 900;
  }
  canvas.height = 180;
}
window.addEventListener('resize', () => {
  resizeCanvas();
  drawBandwidthChart();
});
resizeCanvas();

function drawBandwidthChart() {
  if (!ctx || !canvas) return;

  // Auto-correct width if container became visible after tab switch
  if (canvas.parentElement && canvas.parentElement.clientWidth > 0) {
    if (Math.abs(canvas.width - canvas.parentElement.clientWidth) > 4) {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = 180;
    }
  }

  const w = canvas.width;
  const h = canvas.height;
  if (w <= 0 || h <= 0) return;

  ctx.clearRect(0, 0, w, h);

  const downData = state.bandwidthHistory.download;
  const upData = state.bandwidthHistory.upload;
  const maxVal = Math.max(...downData, ...upData, 1024 * 30); // Minimum 30 KB/s scale

  // Draw background grid lines and scale labels
  ctx.strokeStyle = 'rgba(75, 85, 99, 0.25)';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#9ca3af';
  ctx.font = '10px monospace';
  ctx.textAlign = 'right';

  for (let i = 0; i <= 3; i++) {
    const y = 20 + (i / 3) * (h - 35);
    ctx.beginPath();
    ctx.moveTo(10, y);
    ctx.lineTo(w - 75, y);
    ctx.stroke();

    const valLabel = maxVal * (1 - i / 3);
    const labelText = valLabel >= 1024 * 1024 ? 
      `${(valLabel / (1024 * 1024)).toFixed(1)} MB/s` : 
      `${(valLabel / 1024).toFixed(0)} KB/s`;
    ctx.fillText(labelText, w - 8, y + 3);
  }

  // Helper to draw a curve
  function drawLine(data, strokeColor, fillGradientStart) {
    if (data.length < 2) return;
    const chartW = w - 80; // leave room for labels on right
    const points = data.map((val, idx) => ({
      x: 10 + (chartW / (data.length - 1)) * idx,
      y: (h - 15) - (val / maxVal) * (h - 40)
    }));

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const xc = (points[i - 1].x + points[i].x) / 2;
      const yc = (points[i - 1].y + points[i].y) / 2;
      ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
    }
    ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Fill area under curve
    ctx.lineTo(points[points.length - 1].x, h - 15);
    ctx.lineTo(points[0].x, h - 15);
    ctx.closePath();
    
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, fillGradientStart);
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw glowing circle on latest value
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = strokeColor;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // Draw Upload (Purple / Violet)
  drawLine(upData, '#a855f7', 'rgba(168, 85, 247, 0.25)');
  // Draw Download (Cyan)
  drawLine(downData, '#06b6d4', 'rgba(6, 182, 212, 0.35)');
}

// Fetch Live Network Statistics
async function fetchNetworkStats() {
  try {
    const res = await fetch('/api/network-stats');
    if (!res.ok) return;
    const data = await res.json();
    state.networkStats = data;

    // Update Header Badges & Cards
    if (elements.statDownSpeed) {
      elements.statDownSpeed.textContent = data.bandwidth.download_speed_str;
      elements.statDownTotal.textContent = `Tổng nhận: ${data.bandwidth.total_recv_str}`;
    }
    if (elements.statUpSpeed) {
      elements.statUpSpeed.textContent = data.bandwidth.upload_speed_str;
      elements.statUpTotal.textContent = `Tổng gửi: ${data.bandwidth.total_sent_str}`;
    }

    const chartLiveDown = document.getElementById('chartLiveDown');
    const chartLiveUp = document.getElementById('chartLiveUp');
    if (chartLiveDown) chartLiveDown.textContent = data.bandwidth.download_speed_str;
    if (chartLiveUp) chartLiveUp.textContent = data.bandwidth.upload_speed_str;

    if (elements.statWifiSignal) {
      if (data.wifi.is_wifi) {
        elements.statWifiSignal.textContent = `${data.wifi.signal}%`;
        elements.statWifiMeta.textContent = `${data.wifi.ssid} (${data.wifi.band || '5 GHz'})`;
      } else {
        elements.statWifiSignal.textContent = 'Ethernet';
        elements.statWifiMeta.textContent = data.active_interface;
      }
    }

    // Push into chart history
    state.bandwidthHistory.download.shift();
    state.bandwidthHistory.download.push(data.bandwidth.download_speed_bytes);
    state.bandwidthHistory.upload.shift();
    state.bandwidthHistory.upload.push(data.bandwidth.upload_speed_bytes);
    drawBandwidthChart();

    // Update Network Parameters Tab
    if (elements.paramLocalIp) elements.paramLocalIp.textContent = data.local_ip || 'N/A';
    if (elements.paramActiveIface) elements.paramActiveIface.textContent = data.active_interface || 'N/A';
    if (elements.paramSubnet) elements.paramSubnet.textContent = data.subnet_mask || 'N/A';
    if (elements.paramGateway) elements.paramGateway.textContent = data.gateway || 'N/A';
    if (elements.paramDns) elements.paramDns.textContent = (data.dns_servers || []).join(', ') || 'N/A';
    if (elements.paramMac) elements.paramMac.textContent = data.mac_address || 'N/A';

    if (elements.paramSsid) elements.paramSsid.textContent = data.wifi.ssid || 'N/A';
    if (elements.paramRadioType) elements.paramRadioType.textContent = data.wifi.radio_type || 'N/A';
    if (elements.paramBandChannel) elements.paramBandChannel.textContent = `${data.wifi.band || 'N/A'} (Kênh ${data.wifi.channel || 'N/A'})`;
    if (elements.paramLinkSpeed) elements.paramLinkSpeed.textContent = `Thu: ${data.wifi.receive_rate || 'N/A'} / Phát: ${data.wifi.transmit_rate || 'N/A'}`;
    if (elements.paramBssid) elements.paramBssid.textContent = data.wifi.bssid || 'N/A';

    // Adapters list
    if (elements.adaptersList && data.adapters) {
      elements.adaptersList.innerHTML = data.adapters.map(ad => `
        <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:0.75rem 1rem; margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:600; font-size:0.9rem; color:#fff;">
              ${ad.name}
              ${ad.is_active ? '<span class="role-tag role-localhost">Đang hoạt động</span>' : ''}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted); font-family:var(--font-mono); margin-top:2px;">
              IP: ${ad.ipv4 || 'N/A'} &bull; MAC: ${ad.mac || 'N/A'}
            </div>
          </div>
          <div style="text-align:right;">
            <span class="status-indicator ${ad.is_up ? 'status-online' : 'status-offline'}">
              <span class="status-dot"></span> ${ad.is_up ? 'Kết nối' : 'Ngắt kết nối'}
            </span>
            ${ad.speed_mbps ? `<div style="font-size:0.74rem; color:var(--text-dim); margin-top:2px;">${ad.speed_mbps} Mbps</div>` : ''}
          </div>
        </div>
      `).join('');
    }

  } catch (err) {
    console.error('Error fetching network stats:', err);
  }
}

// Fetch Devices List
async function fetchDevices() {
  try {
    const res = await fetch('/api/devices');
    if (!res.ok) return;
    const data = await res.json();
    state.devices = data.devices;

    if (elements.statOnlineCount) elements.statOnlineCount.textContent = data.online_count;
    if (elements.statTotalCount) elements.statTotalCount.textContent = `/${data.total_count} thiết bị`;

    // Detect new devices for sound alerts
    data.devices.forEach(dev => {
      if (dev.status === 'online' && !state.knownMacs.has(dev.mac)) {
        if (state.knownMacs.size > 0 && dev.is_new) {
          sounds.playDeviceJoined();
          showToast(`Thiết bị mới phát hiện: ${dev.ip} (${dev.vendor || dev.hostname || 'Unknown'})`, 'success', '🔔 Thiết bị mới kết nối');
        }
        state.knownMacs.add(dev.mac);
      }
    });

    renderDevicesTable();
  } catch (err) {
    console.error('Error fetching devices:', err);
  }
}

// Render Devices Table
function renderDevicesTable() {
  if (!elements.devicesTableBody) return;

  const query = state.searchQuery.toLowerCase().trim();
  const filter = state.activeFilter;

  const filtered = state.devices.filter(dev => {
    // Search query filter
    const matchQuery = !query || (
      (dev.ip && dev.ip.toLowerCase().includes(query)) ||
      (dev.mac && dev.mac.toLowerCase().includes(query)) ||
      (dev.hostname && dev.hostname.toLowerCase().includes(query)) ||
      (dev.custom_name && dev.custom_name.toLowerCase().includes(query)) ||
      (dev.vendor && dev.vendor.toLowerCase().includes(query)) ||
      (dev.device_type && dev.device_type.toLowerCase().includes(query))
    );

    if (!matchQuery) return false;

    // Category filter
    if (filter === 'online') return dev.status === 'online';
    if (filter === 'new') return dev.is_new === true;
    if (filter === 'router') return dev.is_gateway === true;
    if (filter === 'pc') return dev.device_type.includes('PC') || dev.is_localhost;
    if (filter === 'mobile') return dev.device_type.includes('Điện thoại') || dev.is_randomized_mac;

    return true;
  });

  if (filtered.length === 0) {
    elements.devicesTableBody.innerHTML = `
      <tr>
        <td colspan="9">
          <div class="empty-state">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>Không tìm thấy thiết bị nào phù hợp</div>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  elements.devicesTableBody.innerHTML = filtered.map(dev => {
    const isOnline = dev.status === 'online';
    const isNew = dev.is_new;
    const isGateway = dev.is_gateway;
    const isLocalhost = dev.is_localhost;

    // Ping badge styling
    let pingBadge = '<span style="color:var(--text-dim);">-</span>';
    if (dev.latency_ms !== null && dev.latency_ms !== undefined) {
      const ms = Math.round(dev.latency_ms);
      const pingClass = ms < 15 ? 'ping-fast' : ms < 60 ? 'ping-medium' : 'ping-slow';
      pingBadge = `<span class="ping-badge ${pingClass}">${ms} ms</span>`;
    }

    // Role badge
    let roleBadge = '';
    if (isLocalhost) roleBadge = '<span class="role-tag role-localhost">Máy tính này</span>';
    else if (isGateway) roleBadge = '<span class="role-tag role-gateway">Router Wi-Fi</span>';

    // Custom name or hostname
    const displayName = dev.custom_name ? 
      `<span style="color:#60a5fa; font-weight:600;">${escapeHtml(dev.custom_name)}</span> <span style="font-size:0.75rem; color:var(--text-dim);">(${escapeHtml(dev.hostname || 'No Hostname')})</span>` :
      `<span style="color:#e5e7eb;">${escapeHtml(dev.hostname || 'Không có tên')}</span>`;

    return `
      <tr class="${isNew ? 'highlight-new' : ''}">
        <td>
          <span class="status-indicator ${isOnline ? 'status-online' : 'status-offline'}">
            <span class="status-dot"></span>
            ${isOnline ? (isNew ? 'Mới vào' : 'Online') : 'Offline'}
          </span>
        </td>
        <td>
          <div class="ip-badge">
            ${dev.ip}
            <button class="copy-btn" title="Sao chép IP" onclick="copyToClipboard('${dev.ip}', 'IP')">
              📋
            </button>
            ${roleBadge}
          </div>
        </td>
        <td>
          <div style="display:flex; align-items:center; gap:0.4rem;">
            ${displayName}
            <button class="copy-btn" title="Đặt tên tùy biến" onclick="openAliasModal('${dev.mac}', '${dev.ip}', '${escapeHtml(dev.custom_name || dev.hostname || '')}')">
              ✏️
            </button>
          </div>
        </td>
        <td>
          <div style="display:flex; align-items:center; gap:0.35rem;">
            <span class="mac-badge">${dev.mac}</span>
            <button class="copy-btn" title="Sao chép MAC" onclick="copyToClipboard('${dev.mac}', 'MAC')">
              📋
            </button>
          </div>
        </td>
        <td>
          <div class="vendor-text">${escapeHtml(dev.vendor || 'Unknown')}</div>
          ${dev.is_randomized_mac ? '<div class="vendor-randomized">🔒 MAC riêng tư (Randomized)</div>' : ''}
        </td>
        <td>
          <span style="font-size:0.8rem; color:var(--text-muted);">${dev.device_type || 'Thiết bị'}</span>
        </td>
        <td>${pingBadge}</td>
        <td>
          <div style="font-size:0.76rem; color:var(--text-muted);">${dev.last_detected || '-'}</div>
          <div style="font-size:0.7rem; color:var(--text-dim);">${dev.detection_count || 1} lần quét</div>
        </td>
        <td>
          <div style="display:flex; gap:0.4rem;">
            <button class="btn btn-secondary btn-sm" title="Kiểm tra Ping" onclick="quickPing('${dev.ip}')">
              Ping
            </button>
            <button class="btn btn-secondary btn-sm" title="Quét cổng dịch vụ" onclick="quickPortScan('${dev.ip}')">
              Cổng
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Quick Ping from table
window.quickPing = function(ip) {
  const pingTab = document.querySelector('[data-tab="tools"]');
  if (pingTab) pingTab.click();
  if (elements.pingInput) {
    elements.pingInput.value = ip;
    elements.btnRunPing.click();
  }
};

// Quick Port Scan from table
window.quickPortScan = function(ip) {
  const pingTab = document.querySelector('[data-tab="tools"]');
  if (pingTab) pingTab.click();
  if (elements.portScanInput) {
    elements.portScanInput.value = ip;
    elements.btnRunPortScan.click();
  }
};

// Polling Scan Status
async function pollScanStatus() {
  try {
    const res = await fetch('/api/scan-status');
    if (!res.ok) return;
    const data = await res.json();
    state.scanStatus = data;

    if (data.is_scanning) {
      elements.btnScanNow.disabled = true;
      elements.btnScanNow.innerHTML = `<span style="display:inline-block; animation:spin 1s linear infinite;">⏳</span> Đang quét (${data.progress}%)...`;
      elements.scanProgressWrapper.classList.add('visible');
      elements.scanProgressBar.style.width = `${data.progress}%`;
      elements.scanPercentText.textContent = `${data.progress}% (${data.scanned}/${data.total} IP)`;
      elements.scanStatusText.textContent = `Tìm thấy ${data.found_count} thiết bị...`;
    } else {
      elements.btnScanNow.disabled = false;
      elements.btnScanNow.innerHTML = `<span>⚡</span> Quét mạng ngay`;
      elements.scanProgressWrapper.classList.remove('visible');
    }
  } catch (err) {
    console.error('Error polling scan status:', err);
  }
}

// Trigger Manual Scan
if (elements.btnScanNow) {
  elements.btnScanNow.addEventListener('click', async () => {
    sounds.init();
    try {
      elements.btnScanNow.disabled = true;
      elements.btnScanNow.innerHTML = `<span>⏳</span> Đang chuẩn bị...`;
      
      const customRange = document.getElementById('scanRangeInput') ? document.getElementById('scanRangeInput').value : null;

      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ range: customRange })
      });
      const data = await res.json();
      if (data.success) {
        showToast('Đang quét tất cả thiết bị trên mạng...', 'info');
      } else {
        showToast(data.message || 'Không thể bắt đầu quét', 'warning');
      }
    } catch (err) {
      showToast('Lỗi khi gửi yêu cầu quét', 'warning');
    }
  });
}

// Auto-Scan Interval Dropdown
if (elements.autoScanSelect) {
  elements.autoScanSelect.addEventListener('change', async (e) => {
    const val = parseInt(e.target.value);
    const enabled = val > 0;
    try {
      await fetch('/api/auto-scan-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, interval: val || 30 })
      });
      showToast(`Tự động quét: ${enabled ? `mỗi ${val} giây` : 'Tắt'}`, 'info');
    } catch (err) {
      console.error(err);
    }
  });
}

// Search and Filter Events
if (elements.searchInput) {
  elements.searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value;
    renderDevicesTable();
  });
}

elements.filterPills.forEach(pill => {
  pill.addEventListener('click', () => {
    elements.filterPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.activeFilter = pill.dataset.filter;
    renderDevicesTable();
  });
});

// Modal Custom Alias / Rename
window.openAliasModal = function(mac, ip, currentName) {
  elements.aliasMacInput.value = mac;
  elements.aliasNameInput.value = currentName || '';
  elements.aliasTargetDesc.textContent = `${ip} &bull; ${mac}`;
  elements.aliasModal.classList.add('active');
  setTimeout(() => elements.aliasNameInput.focus(), 100);
};

function closeAliasModal() {
  elements.aliasModal.classList.remove('active');
}

if (elements.modalCloseBtn) elements.modalCloseBtn.addEventListener('click', closeAliasModal);
if (elements.btnCancelAlias) elements.btnCancelAlias.addEventListener('click', closeAliasModal);

if (elements.btnSaveAlias) {
  elements.btnSaveAlias.addEventListener('click', async () => {
    const mac = elements.aliasMacInput.value;
    const alias = elements.aliasNameInput.value.trim();
    try {
      const res = await fetch('/api/device/alias', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mac, alias })
      });
      if (res.ok) {
        showToast('Đã lưu tên thiết bị thành công!', 'success');
        closeAliasModal();
        fetchDevices();
      }
    } catch (err) {
      showToast('Lỗi khi lưu tên thiết bị', 'warning');
    }
  });
}

// Clear History Button
const btnClearHistory = document.getElementById('btnClearHistory');
if (btnClearHistory) {
  btnClearHistory.addEventListener('click', async () => {
    if (confirm('Bạn có chắc muốn xóa lịch sử các thiết bị đã phát hiện và quét lại từ đầu?')) {
      try {
        await fetch('/api/clear-history', { method: 'POST' });
        state.knownMacs.clear();
        showToast('Đã làm mới dữ liệu và bắt đầu quét mới', 'info');
        fetchDevices();
      } catch (err) {
        showToast('Lỗi khi làm mới', 'warning');
      }
    }
  });
}

// Ping Tool Execution
if (elements.btnRunPing) {
  elements.btnRunPing.addEventListener('click', async () => {
    const host = elements.pingInput.value.trim();
    if (!host) {
      showToast('Vui lòng nhập IP hoặc tên miền cần Ping', 'warning');
      return;
    }

    elements.btnRunPing.disabled = true;
    elements.pingOutput.textContent = `Đang gửi 4 gói tin Ping đến ${host}...\n`;

    try {
      const res = await fetch('/api/tools/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host })
      });
      const data = await res.json();
      if (data.success) {
        elements.pingOutput.textContent = data.output;
      } else {
        elements.pingOutput.textContent = `Lỗi: ${data.error}`;
      }
    } catch (err) {
      elements.pingOutput.textContent = `Lỗi kết nối tới server: ${err.message}`;
    } finally {
      elements.btnRunPing.disabled = false;
    }
  });
}

// Port Scan Tool Execution
if (elements.btnRunPortScan) {
  elements.btnRunPortScan.addEventListener('click', async () => {
    const ip = elements.portScanInput.value.trim();
    if (!ip) {
      showToast('Vui lòng nhập IP cần kiểm tra cổng', 'warning');
      return;
    }

    elements.btnRunPortScan.disabled = true;
    elements.portScanOutput.textContent = `Đang quét các cổng dịch vụ phổ biến trên ${ip} (HTTP, HTTPS, SSH, SMB, RDP...)...\n`;

    try {
      const res = await fetch('/api/tools/port-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip })
      });
      const data = await res.json();
      if (data.success) {
        if (data.open_ports.length === 0) {
          elements.portScanOutput.textContent = `Hoàn tất: Không có cổng phổ biến nào mở (Thiết bị có thể bật tường lửa hoặc không chạy dịch vụ server).`;
        } else {
          let output = `✅ TÌM THẤY ${data.open_ports.length} CỔNG ĐANG MỞ TRÊN ${ip}:\n`;
          output += `----------------------------------------\n`;
          data.open_ports.forEach(p => {
            output += `[CỔNG ${p.port}] -> ${p.service}\n`;
          });
          output += `----------------------------------------\n`;
          elements.portScanOutput.textContent = output;
        }
      } else {
        elements.portScanOutput.textContent = `Lỗi: ${data.error}`;
      }
    } catch (err) {
      elements.portScanOutput.textContent = `Lỗi: ${err.message}`;
    } finally {
      elements.btnRunPortScan.disabled = false;
    }
  });
}

// =========================================================================
// Wi-Fi APs & Signal (dBm) Scanner Logic
// =========================================================================
const wifiApsTableBody = document.getElementById('wifiApsTableBody');
const btnScanWifiAps = document.getElementById('btnScanWifiAps');

async function fetchWifiAps() {
  if (!wifiApsTableBody) return;
  if (btnScanWifiAps) {
    btnScanWifiAps.disabled = true;
    btnScanWifiAps.innerHTML = `<span>⏳</span> Đang quét sóng Wi-Fi...`;
  }
  wifiApsTableBody.innerHTML = `
    <tr>
      <td colspan="9" style="text-align:center; padding: 2.5rem; color: var(--text-dim);">
        Đang quét tất cả các trạm phát sóng Wi-Fi lân cận...
      </td>
    </tr>
  `;

  try {
    const res = await fetch('/api/wifi-networks');
    const data = await res.json();

    if (!data.networks || data.networks.length === 0) {
      wifiApsTableBody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align:center; padding: 2.5rem; color: var(--text-dim);">
            Không phát hiện được mạng Wi-Fi nào (hoặc card Wi-Fi đang tắt)
          </td>
        </tr>
      `;
      return;
    }

    wifiApsTableBody.innerHTML = data.networks.map(n => {
      // Color based on dBm strength:
      // > -60 dBm: Excellent (Green)
      // -60 to -75 dBm: Good (Cyan / Blue)
      // -75 to -85 dBm: Fair (Amber)
      // < -85 dBm: Weak (Red)
      const dbm = n.signal_dbm;
      let badgeClass = 'ping-slow';
      if (dbm >= -60) badgeClass = 'ping-fast';
      else if (dbm >= -75) badgeClass = 'ping-medium';

      return `
        <tr>
          <td>
            <div style="font-weight:700; color:#fff; display:flex; align-items:center; gap:0.4rem;">
              <span>📶</span> ${escapeHtml(n.ssid)}
            </div>
          </td>
          <td>
            <span class="ping-badge ${badgeClass}" style="font-size:0.85rem;">
              ${n.signal_dbm} dBm
            </span>
          </td>
          <td>
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <span style="font-weight:600; font-size:0.85rem; color:#fff; min-width:32px;">${n.signal_pct}%</span>
              <div style="width:70px; height:6px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                <div style="width:${n.signal_pct}%; height:100%; background:linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));"></div>
              </div>
            </div>
          </td>
          <td>
            <span class="mac-badge">${n.bssid}</span>
          </td>
          <td>
            <span style="font-family:var(--font-mono); font-weight:600; color:#fff;">${n.channel || '-'}</span>
          </td>
          <td>
            <span style="font-size:0.8rem; color:var(--text-muted);">${n.band || '-'}</span>
          </td>
          <td>
            <span style="font-size:0.8rem; color:var(--accent-cyan); font-weight:600;">${n.radio_type || '-'}</span>
          </td>
          <td>
            <span style="font-size:0.78rem; color:var(--text-muted);">${n.auth || '-'}</span>
          </td>
          <td>
            <span style="font-size:0.8rem; color:${n.connected_stations ? '#60a5fa' : 'var(--text-dim)'}; font-weight:600;">
              ${n.connected_stations !== null && n.connected_stations !== undefined ? `${n.connected_stations} máy` : '-'}
            </span>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    wifiApsTableBody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align:center; padding: 2rem; color: var(--accent-red);">
          Lỗi khi quét trạm Wi-Fi: ${err.message}
        </td>
      </tr>
    `;
  } finally {
    if (btnScanWifiAps) {
      btnScanWifiAps.disabled = false;
      btnScanWifiAps.innerHTML = `<span>🔄</span> Quét lại sóng Wi-Fi (dBm)`;
    }
  }
}

if (btnScanWifiAps) {
  btnScanWifiAps.addEventListener('click', fetchWifiAps);
}

// Auto-fetch Wi-Fi APs when user clicks the Wi-Fi APs tab
document.querySelectorAll('.tab-btn').forEach(btn => {
  if (btn.dataset.tab === 'wifi-aps') {
    btn.addEventListener('click', fetchWifiAps);
  }
});

// =========================================================================
// Database (DB) Server Scanner Tool Logic
// =========================================================================
const dbScanInput = document.getElementById('dbScanInput');
const btnRunDbScan = document.getElementById('btnRunDbScan');
const dbScanOutput = document.getElementById('dbScanOutput');

if (btnRunDbScan) {
  btnRunDbScan.addEventListener('click', async () => {
    const targetIp = dbScanInput ? dbScanInput.value.trim() : '';
    btnRunDbScan.disabled = true;
    btnRunDbScan.innerHTML = `<span>⏳</span> Đang dò tìm Database...`;
    
    if (targetIp) {
      dbScanOutput.textContent = `Đang quét các dịch vụ Database trên ${targetIp}...\n`;
    } else {
      dbScanOutput.textContent = `Đang quét các dịch vụ Database (MySQL, Postgres, MSSQL, MongoDB, Redis, Oracle...) trên toàn bộ thiết bị đang online trong mạng...\n`;
    }

    try {
      const res = await fetch('/api/tools/database-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: targetIp })
      });
      const data = await res.json();

      if (data.success) {
        if (data.databases.length === 0) {
          dbScanOutput.textContent += `\nHoàn tất: Đã kiểm tra ${data.scanned_ips.length} thiết bị, KHÔNG tìm thấy cổng Database nào đang mở công khai.`;
        } else {
          let out = `\n🎉 TÌM THẤY ${data.databases.length} DỊCH VỤ DATABASE ĐANG MỞ:\n`;
          out += `====================================================\n`;
          data.databases.forEach(db => {
            out += `[+] ${db.ip}:${db.port}  ==>  ${db.database}\n`;
          });
          out += `====================================================\n`;
          out += `Đã quét tổng cộng: ${data.scanned_ips.length} địa chỉ IP.`;
          dbScanOutput.textContent = out;
        }
      } else {
        dbScanOutput.textContent = `Lỗi quét Database: ${data.error}`;
      }
    } catch (err) {
      dbScanOutput.textContent = `Lỗi kết nối: ${err.message}`;
    } finally {
      btnRunDbScan.disabled = false;
      btnRunDbScan.innerHTML = `<span>🚀</span> Quét Database (DB)`;
    }
  });
}

// Global Click sound listener to unlock AudioContext in modern browsers
window.addEventListener('click', () => sounds.init(), { once: true });

// Periodic Loops
setInterval(fetchNetworkStats, 1000); // 1s live bandwidth & network stats
setInterval(pollScanStatus, 600);     // 600ms progress tracker
setInterval(fetchDevices, 4000);       // 4s device list refresh

// Initial Load
fetchNetworkStats();
fetchDevices();
pollScanStatus();

