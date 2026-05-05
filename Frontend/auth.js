export const API_BASE = "";

export function getToken() {
  return sessionStorage.getItem("google_token");
}

export async function authHeaders(extra = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...extra };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export function requireAuth(callback) {
  const token = getToken();
  if (!token) {
    window.location.href = "login.html";
    return;
  }
  const expiresAt = Number(sessionStorage.getItem("token_expires_at") || 0);
  if (expiresAt && Date.now() > expiresAt) {
    signOut();
    window.location.href = "login.html";
    return;
  }
  let userInfo = {};
  try {
    userInfo = JSON.parse(sessionStorage.getItem("user_info") || "{}");
  } catch {
    signOut();
    window.location.href = "login.html";
    return;
  }
  callback(userInfo);
}

export function signOut() {
  sessionStorage.removeItem("google_token");
  sessionStorage.removeItem("user_info");
  sessionStorage.removeItem("token_expires_at");
}

export async function fetchWithAuth(url, options = {}) {
  const headers = await authHeaders(options.headers || {});
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    signOut();
    window.location.href = "login.html";
    throw new Error("Sesión expirada");
  }
  return response;
}
