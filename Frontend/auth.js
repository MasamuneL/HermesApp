export const API_BASE = "";

export function getToken() {
  return sessionStorage.getItem("google_token");
}

export async function authHeaders(extra = {}) {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getToken()}`,
    ...extra,
  };
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
  const userInfo = JSON.parse(sessionStorage.getItem("user_info") || "{}");
  callback(userInfo);
}

export function signOut() {
  sessionStorage.removeItem("google_token");
  sessionStorage.removeItem("user_info");
  sessionStorage.removeItem("token_expires_at");
}

export async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    signOut();
    window.location.href = "login.html";
    throw new Error("Sesión expirada");
  }
  return response;
}
