const API_BASE_URL = "http://localhost:8000";

/* ─── Token Storage ─── */
export function getToken() {
  return localStorage.getItem("jwt_token");
}

export function clearToken() {
  localStorage.removeItem("jwt_token");
}

/* ─── Auth Guard – call at start of dashboard JS ─── */
export function requireAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

/* ─── Authenticated fetch wrapper ─── */
export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  
  if (!(options.body instanceof FormData) && !("Content-Type" in headers)) {
    headers["Content-Type"] = "application/json";
  }
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });

  // Token expired or invalid — redirect to login
  if (res.status === 401) {
    clearToken();
    window.location.href = "login.html";
    throw new Error("Session expired. Please log in again.");
  }

  return res;
}

/* ─── Logout ─── */
export function logout() {
  clearToken();
  window.location.href = "login.html";
}
