
function getToken() {
  return localStorage.getItem("token");
}

function getUser() {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

function setAuth(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

async function apiRequest(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.detail
      ? typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail)
      : "Request failed";
    throw new Error(message);
  }

  return data;
}

function requireAuth(allowedRoles = []) {
  const user = getUser();
  if (!user || !getToken()) {
    window.location.href = "login.html";
    return null;
  }
  if (allowedRoles.length && !allowedRoles.includes(user.role)) {
    window.location.href = redirectByRole(user.role);
    return null;
  }
  return user;
}

function redirectByRole(role) {
  if (role === "admin") return "dashboard.html";
  if (role === "teacher") return "attendance.html";
  if (role === "student") return "profile.html";
  return "index.html";
}

function logout() {
  clearAuth();
  window.location.href = "login.html";
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function showAlert(containerId, message, type = "error") {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

function clearAlert(containerId) {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = "";
}

function renderNavbar(activePage = "") {
  const user = getUser();
  const nav = document.getElementById("nav-links");
  if (!nav) return;

  const publicLinks = `
    <a href="index.html" class="${activePage === "home" ? "active" : ""}">Home</a>
    <a href="about.html" class="${activePage === "about" ? "active" : ""}">About</a>
  `;

  if (!user) {
    nav.innerHTML = `${publicLinks}<a href="login.html">Login</a>`;
    return;
  }

  let roleLinks = "";
  if (user.role === "admin") {
    roleLinks = `
      <a href="dashboard.html" class="${activePage === "dashboard" ? "active" : ""}">Dashboard</a>
      <a href="students.html" class="${activePage === "students" ? "active" : ""}">Students</a>
      <a href="courses.html" class="${activePage === "courses" ? "active" : ""}">Courses</a>
      <a href="announcements.html" class="${activePage === "announcements" ? "active" : ""}">Announcements</a>
    `;
  } else if (user.role === "teacher") {
    roleLinks = `
      <a href="attendance.html" class="${activePage === "attendance" ? "active" : ""}">Attendance</a>
      <a href="grades.html" class="${activePage === "grades" ? "active" : ""}">Grades</a>
      <a href="announcements.html" class="${activePage === "announcements" ? "active" : ""}">Announcements</a>
    `;
  } else {
    roleLinks = `
      <a href="profile.html" class="${activePage === "profile" ? "active" : ""}">My Profile</a>
      <a href="announcements.html" class="${activePage === "announcements" ? "active" : ""}">Announcements</a>
    `;
  }

  nav.innerHTML = `
    ${publicLinks}
    ${roleLinks}
    <span style="color:#e2e8f0;">${user.full_name} (${user.role})</span>
    <a href="#" id="logout-btn">Logout</a>
  `;

  document.getElementById("logout-btn")?.addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });
}
