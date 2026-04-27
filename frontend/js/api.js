// js/api.js — API client

const API = window.API_URL || 'https://ops-system.onrender.com/api';
const SUPABASE_URL = window.SUPABASE_URL || 'https://jmbczkhjrewsqqfdhiry.supabase.co';
const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || '';

// ── Auth ──────────────────────────────────────────────────────
async function signIn(email, password) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY },
    body: JSON.stringify({ email, password }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error_description || data.msg || 'Login failed');
  return data;
}

async function signOut() {
  const token = getToken();
  if (token) {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY, 'Authorization': `Bearer ${token}` },
    }).catch(() => {});
  }
  localStorage.removeItem('ops_token');
  localStorage.removeItem('ops_profile');
  window.location.href = '/index.html';
}

function getToken() { return localStorage.getItem('ops_token'); }
function getProfile() {
  const p = localStorage.getItem('ops_profile');
  return p ? JSON.parse(p) : null;
}
function saveSession(token, profile) {
  localStorage.setItem('ops_token', token);
  localStorage.setItem('ops_profile', JSON.stringify(profile));
}

function requireAuth() {
  const token = getToken();
  const profile = getProfile();
  if (!token || !profile) {
    window.location.href = '/index.html';
    return null;
  }
  return profile;
}

function requireRole(...roles) {
  const profile = requireAuth();
  if (!profile) return null;
  if (!roles.includes(profile.role)) {
    window.location.href = '/dashboard.html';
    return null;
  }
  return profile;
}

// ── Fetch wrapper ─────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const r = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || data.error || 'API error');
  return data;
}

// ── Tasks ─────────────────────────────────────────────────────
const Tasks = {
  getAll: ()           => apiFetch('/tasks'),
  getWorkload: ()      => apiFetch('/tasks/staff-workload'),
  create: (body)       => apiFetch('/tasks', { method: 'POST', body: JSON.stringify(body) }),
  update: (id, body)   => apiFetch(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id)         => apiFetch(`/tasks/${id}`, { method: 'DELETE' }),
};

// ── Attendance ────────────────────────────────────────────────
const Attendance = {
  checkIn: (body)   => apiFetch('/attendance/checkin', { method: 'POST', body: JSON.stringify(body) }),
  complete: (body)  => apiFetch('/attendance/complete', { method: 'POST', body: JSON.stringify(body) }),
  getLogs: ()       => apiFetch('/attendance'),
};

// ── Users ─────────────────────────────────────────────────────
const Users = {
  getAll: ()           => apiFetch('/auth/users'),
  create: (body)       => apiFetch('/auth/users', { method: 'POST', body: JSON.stringify(body) }),
  update: (id, body)   => apiFetch(`/auth/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deactivate: (id)     => apiFetch(`/auth/users/${id}`, { method: 'DELETE' }),
};

// ── Notifications ─────────────────────────────────────────────
const Notifications = {
  getVapidKey: () => apiFetch('/notifications/vapid-public-key'),
  subscribe: (body) => apiFetch('/notifications/subscribe', { method: 'POST', body: JSON.stringify(body) }),
  test: () => apiFetch('/notifications/test', { method: 'POST' }),
};

// ── Supabase Realtime (simple polling fallback) ───────────────
function pollRealtime(callback, interval = 5000) {
  return setInterval(callback, interval);
}

// ── Chat via Supabase REST ────────────────────────────────────
async function getMessages(partnerId) {
  const myId = getProfile()?.id;
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/messages?select=*,sender:profiles!messages_sender_id_fkey(id,full_name,role)&or=(and(sender_id.eq.${myId},receiver_id.eq.${partnerId}),and(sender_id.eq.${partnerId},receiver_id.eq.${myId}))&order=created_at.asc&limit=100`,
    { headers: { 'apikey': SUPABASE_ANON_KEY, 'Authorization': `Bearer ${getToken()}` } }
  );
  return r.json();
}

async function sendMessage(receiverId, content) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SUPABASE_ANON_KEY,
      'Authorization': `Bearer ${getToken()}`,
      'Prefer': 'return=representation',
    },
    body: JSON.stringify({ sender_id: getProfile()?.id, receiver_id: receiverId, content }),
  });
  return r.json();
}

async function getContacts() {
  const profile = getProfile();
  let filter = '';
  if (profile?.role === 'staff') {
    filter = '&role=in.(manager,admin)';
  } else {
    filter = `&id=neq.${profile?.id}`;
  }
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/profiles?select=id,full_name,role&is_active=eq.true${filter}&order=full_name.asc`,
    { headers: { 'apikey': SUPABASE_ANON_KEY, 'Authorization': `Bearer ${getToken()}` } }
  );
  return r.json();
}

// ── GPS ───────────────────────────────────────────────────────
function getGPS() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Geolocation not supported'));
    navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 });
  });
}

// ── Helpers ───────────────────────────────────────────────────
function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(d) {
  if (!d) return '';
  return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function taskTypeIcon(type) {
  return { bank: '🏦', delivery: '📦', party: '🎉' }[type] || '📋';
}

function taskTypeColor(type) {
  return { bank: 'amber', delivery: 'cyan', party: 'purple' }[type] || 'cyan';
}

function roleColor(role) {
  return { admin: 'red', manager: 'amber', staff: 'cyan' }[role] || 'muted';
}

function statusBadge(status) {
  return `<span class="badge badge-${status}">${status.replace('_', ' ')}</span>`;
}

// ── PWA Registration ──────────────────────────────────────────
async function registerPWA() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register('/sw.js');
    console.log('[SW] Registered');
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission();
    }
    // Subscribe to push
    if (Notification.permission === 'granted' && 'PushManager' in window) {
      try {
        const { publicKey } = await Notifications.getVapidKey();
        if (publicKey) {
          const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
          });
          const json = sub.toJSON();
          await Notifications.subscribe({ endpoint: json.endpoint, keys: json.keys, userAgent: navigator.userAgent });
        }
      } catch (e) { console.warn('[Push]', e.message); }
    }
  } catch (e) { console.warn('[SW]', e); }
}

function urlBase64ToUint8Array(base64) {
  const pad = '='.repeat((4 - base64.length % 4) % 4);
  const b64 = (base64 + pad).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(b64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

// ── Sidebar active state ──────────────────────────────────────
function setActiveNav() {
  const path = window.location.pathname.split('/').pop() || 'dashboard.html';
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('href') === path);
  });
}

// ── Init sidebar profile ──────────────────────────────────────
function initSidebar() {
  const profile = getProfile();
  if (!profile) return;

  const nameEl = document.getElementById('profile-name');
  const roleEl = document.getElementById('profile-role');
  const avatarEl = document.getElementById('profile-avatar');

  if (nameEl) nameEl.textContent = profile.full_name || profile.email?.split('@')[0];
  if (roleEl) { roleEl.textContent = profile.role; roleEl.className = `profile-role role-${profile.role}`; }
  if (avatarEl) avatarEl.textContent = (profile.full_name || 'U').charAt(0).toUpperCase();

  // Hide nav items based on role
  document.querySelectorAll('[data-roles]').forEach(el => {
    const roles = el.dataset.roles.split(',');
    if (!roles.includes(profile.role)) el.style.display = 'none';
  });

  setActiveNav();

  // Mobile menu
  const menuBtn = document.getElementById('menu-btn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  if (menuBtn && sidebar) {
    menuBtn.onclick = () => { sidebar.classList.toggle('open'); overlay?.classList.toggle('open'); };
    overlay?.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('open'); });
  }

  // Sign out
  document.getElementById('sign-out-btn')?.addEventListener('click', signOut);
}

// ── Topbar date ───────────────────────────────────────────────
function initTopbar(title) {
  const t = document.getElementById('topbar-title');
  if (t) t.textContent = title || '';
  const d = document.getElementById('topbar-date');
  if (d) d.textContent = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}
