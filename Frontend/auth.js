/**
 * auth.js — Módulo de autenticación con Google OAuth.
 *
 * Reemplaza firebase.js. Usa Google Identity Services (GIS) para obtener
 * el access token, que se almacena en sessionStorage y se usa tanto para
 * autenticar peticiones al backend como para la Google Calendar API.
 *
 * El login con Google se maneja en login.html.
 * Este módulo provee los helpers para las páginas protegidas.
 */

export const API_BASE = "http://localhost:8000";

/** Obtiene el access token almacenado en sessionStorage. */
export function getToken() {
  return sessionStorage.getItem("google_token");
}

/**
 * Headers base para todas las peticiones al backend.
 * El access token de Google sirve tanto para auth como para Calendar API.
 */
export async function authHeaders(extra = {}) {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getToken()}`,
    ...extra,
  };
}

/**
 * Redirige al login si no hay sesión activa.
 * Llama callback(userInfo) si hay token almacenado.
 * userInfo: { email, name, sub, picture }
 */
export function requireAuth(callback) {
  const token = getToken();
  if (!token) {
    window.location.href = "login.html";
    return;
  }
  const userInfo = JSON.parse(sessionStorage.getItem("user_info") || "{}");
  callback(userInfo);
}

/**
 * Cierra la sesión: limpia sessionStorage.
 * El caller es responsable de redirigir al login.
 */
export function signOut() {
  sessionStorage.removeItem("google_token");
  sessionStorage.removeItem("user_info");
}
