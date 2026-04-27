// js/layout.js — Shared sidebar + shell injected into every page

function renderShell(pageTitle) {
  const profile = getProfile();
  if (!profile) return;

  const navItems = {
    admin: [
      { href: 'dashboard.html', icon: '📊', label: 'Dashboard' },
      { href: 'tasks.html',     icon: '✅', label: 'Tasks' },
      { href: 'users.html',     icon: '👥', label: 'Users',     roles: 'admin' },
      { href: 'staff.html',     icon: '👤', label: 'Staff',     roles: 'admin,manager' },
      { href: 'map.html',       icon: '🗺️', label: 'Live Map' },
      { href: 'logs.html',      icon: '📋', label: 'Logs' },
      { href: 'chat.html',      icon: '💬', label: 'Messages' },
    ],
    manager: [
      { href: 'dashboard.html', icon: '📊', label: 'Dashboard' },
      { href: 'tasks.html',     icon: '✅', label: 'Tasks' },
      { href: 'staff.html',     icon: '👤', label: 'Staff' },
      { href: 'map.html',       icon: '🗺️', label: 'Live Map' },
      { href: 'logs.html',      icon: '📋', label: 'Logs' },
      { href: 'chat.html',      icon: '💬', label: 'Messages' },
    ],
    staff: [
      { href: 'dashboard.html', icon: '📊', label: 'My Tasks' },
      { href: 'checkin.html',   icon: '📍', label: 'Check-In' },
      { href: 'map.html',       icon: '🗺️', label: 'Map' },
      { href: 'chat.html',      icon: '💬', label: 'Messages' },
    ],
  };

  const items = navItems[profile.role] || navItems.staff;
  const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';

  const navHTML = items.map(item => `
    <a href="${item.href}" class="nav-item ${currentPage === item.href ? 'active' : ''}">
      <span class="icon">${item.icon}</span>
      <span>${item.label}</span>
    </a>
  `).join('');

  const shell = `
    <div class="app-shell">
      <div class="overlay" id="overlay"></div>

      <!-- Sidebar -->
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo">
          <div class="logo-icon">⚡</div>
          <div>
            <div class="logo-text">OPS<span>SYSTEM</span></div>
            <div class="logo-sub">Operations Hub</div>
          </div>
        </div>

        <div class="sidebar-profile">
          <div class="avatar" id="profile-avatar">${(profile.full_name || 'U').charAt(0).toUpperCase()}</div>
          <div style="flex:1;min-width:0;">
            <div class="profile-name truncate">${profile.full_name || profile.email?.split('@')[0]}</div>
            <div class="profile-role role-${profile.role}">${profile.role}</div>
          </div>
        </div>

        <nav class="nav">${navHTML}</nav>

        <div class="sidebar-footer">
          <button class="btn-signout" id="sign-out-btn">🚪 Sign Out</button>
        </div>
      </aside>

      <!-- Main -->
      <div class="main">
        <header class="topbar">
          <button class="menu-btn" id="menu-btn">☰</button>
          <span class="topbar-title" id="topbar-title">${pageTitle}</span>
          <span class="topbar-date" id="topbar-date"></span>
        </header>
        <div class="page" id="page-content">
          <!-- page content injected here -->
        </div>
      </div>
    </div>
  `;

  document.body.innerHTML = shell;
  document.getElementById('sign-out-btn').addEventListener('click', signOut);
  document.getElementById('topbar-date').textContent = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

  const menuBtn = document.getElementById('menu-btn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  menuBtn?.addEventListener('click', () => { sidebar.classList.toggle('open'); overlay.classList.toggle('open'); });
  overlay?.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('open'); });
}

function getPageContent() {
  return document.getElementById('page-content');
}
