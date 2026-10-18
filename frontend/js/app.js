// HSBLearn Shared Client Utilities
const API_BASE = '/api';

// Theme Management (Light & Dark)
function initTheme() {
  const savedTheme = localStorage.getItem('hsblearn_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('hsblearn_theme', theme);
  const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
  themeToggleBtns.forEach(btn => {
    btn.innerHTML = theme === 'dark' ? '☀️ <span class="hidden sm:inline text-xs">Light</span>' : '🌙 <span class="hidden sm:inline text-xs">Dark</span>';
    btn.setAttribute('title', `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`);
  });
}

function toggleTheme() {
  const current = localStorage.getItem('hsblearn_theme') === 'dark' ? 'dark' : 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
}

// Automatically apply theme on script load
initTheme();
document.addEventListener('DOMContentLoaded', initTheme);

function getToken() {
  return localStorage.getItem('hsblearn_token');
}

function getUser() {
  const user = localStorage.getItem('hsblearn_user');
  return user ? JSON.parse(user) : null;
}

function setAuth(token, user) {
  localStorage.setItem('hsblearn_token', token);
  localStorage.setItem('hsblearn_user', JSON.stringify(user));
}

function logout() {
  localStorage.removeItem('hsblearn_token');
  localStorage.removeItem('hsblearn_user');
  window.location.href = '/static/index.html';
}

function authHeaders() {
  const token = getToken();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!options.isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const config = {
    ...options,
    headers: headers
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, config);
    if (res.status === 401) {
      logout();
      return null;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'An unexpected server error occurred.');
    }
    return data;
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

function checkAuth(requiredRole = null) {
  const user = getUser();
  const token = getToken();
  if (!token || !user) {
    window.location.href = '/static/index.html';
    return null;
  }
  if (requiredRole && user.role !== requiredRole) {
    alert(`Access Denied: This area requires a ${requiredRole} account.`);
    window.location.href = user.role === 'instructor' ? '/static/instructor.html' : '/static/student.html';
    return null;
  }
  return user;
}
