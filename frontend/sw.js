// sw.js — PWA Service Worker
const CACHE = 'ops-v1';
const STATIC = ['/', '/index.html', '/dashboard.html', '/tasks.html', '/chat.html', '/checkin.html', '/css/app.css', '/js/api.js', '/js/config.js', '/js/layout.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; }).catch(() => caches.match(e.request)));
});

self.addEventListener('push', e => {
  let data = {};
  try { data = e.data?.json() || {}; } catch { data = { title: 'OpsSystem', body: e.data?.text() || '' }; }
  e.waitUntil(self.registration.showNotification(data.title || 'OpsSystem', {
    body: data.body || '', icon: '/icons/icon-192.png', badge: '/icons/badge-72.png',
    tag: data.tag || 'default', data: data.data || {}, vibrate: [200,100,200],
  }));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/dashboard.html';
  e.waitUntil(clients.matchAll({ type:'window' }).then(list => {
    for (const c of list) { if (c.url.includes(self.location.origin)) { c.navigate(url); return c.focus(); } }
    return clients.openWindow(url);
  }));
});
