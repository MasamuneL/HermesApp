---
phase: auth-bug-fix
reviewed: 2026-04-24T00:00:00Z
depth: deep
files_reviewed: 7
files_reviewed_list:
  - backend/app/dependencies/auth.py
  - Frontend/auth.js
  - Frontend/main.html
  - Frontend/perfil.html
  - Frontend/ranking.html
  - Frontend/logros.html
  - Frontend/calendario.html
findings:
  critical: 3
  warning: 5
  info: 4
  total: 12
status: issues_found
---

# Auth Bug-Fix: Code Review Report

**Reviewed:** 2026-04-24
**Depth:** deep
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The three targeted bug fixes are implemented correctly: `userinfo` instead of `tokeninfo` in the backend resolves the `name` field issue; `fetchWithAuth` is consistently imported and used across all protected pages; and all authenticated backend calls in the reviewed pages go through the wrapper. No auth bypass regressions were introduced by the changes themselves.

However, the cross-file deep analysis surfaced several issues that were pre-existing or introduced alongside the fix: two stored XSS vectors (one in `calendario.html` driven by Gemini output, one in `logros.html` driven by achievement text), a logic bug in `logros.html` that silently accepts a failed PATCH as a success, a missing `return` in `fetchWithAuth` that causes a redirect race, stale headers in the FullCalendar callback, and a raw `fetch()` left in `ranking.html` that is intentionally unauthenticated but inconsistent with the rest of the codebase.

---

## Critical Issues

### CR-01: XSS — Gemini/bot responses injected via `innerHTML` in `appendMsg`

**File:** `Frontend/calendario.html:513`
**Issue:** `appendMsg(text, type)` sets `div.innerHTML = \`${text}<div class="msg-time">...\``. When `type === "bot"`, `text` is `data.response` — the raw string returned by the Gemini backend. If the backend (or an MITM on the insecure `http://localhost:8000` base URL) returns a string containing HTML tags, those tags are parsed and executed by the browser. The same function is also called with user-typed input (`text = input.value.trim()`, line 404), which is a self-XSS vector and, more importantly, means any script tags a user types are rendered and executed immediately in their own session. The greeting message (line 320) has the same problem: `greetEl.innerHTML = text.replace(/\n/g, "<br>")` uses innerHTML on backend-supplied text.

**Fix:**
```javascript
function appendMsg(text, type) {
  const msgs = document.getElementById("chatMessages");
  const div  = document.createElement("div");
  div.className = `msg ${type}`;
  // Use a text node for the message body, then append the time separately
  const textNode = document.createTextNode(text);
  div.appendChild(textNode);
  const timeDiv = document.createElement("div");
  timeDiv.className = "msg-time";
  timeDiv.textContent = getTime();
  div.appendChild(timeDiv);
  msgs.appendChild(div);
  scrollChat();
}
```
Apply the same pattern to `setGreeting`: replace `text.replace(/\n/g, "<br>")` by splitting on `\n` and appending text nodes with `<br>` elements between them.

---

### CR-02: XSS — Event title from Google Calendar injected into `onclick` attribute string in schedule panel

**File:** `Frontend/calendario.html:630`
**Issue:** The schedule panel builds HTML with:
```javascript
<button ... onclick="editWithGemini('${e.title.replace(/'/g,"\\'")}','${e.start}')">
```
Only single quotes are escaped. A Google Calendar event with a title containing a double quote or closing parenthesis (e.g., `My "Event") // `) breaks out of the string context and injects arbitrary JavaScript into the `onclick` handler. Since event titles come from Google Calendar API (user-controlled data), this is a realistic attack surface.

**Fix:** Do not embed untrusted data in inline event handlers. Store the data in a `data-*` attribute and attach the handler via JavaScript:
```javascript
// In the template:
`<button class="sp-edit-btn"
  data-title="${encodeURIComponent(e.title)}"
  data-start="${encodeURIComponent(e.start)}">Editar</button>`

// After setting list.innerHTML, attach handlers:
list.querySelectorAll(".sp-edit-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    editWithGemini(
      decodeURIComponent(btn.dataset.title),
      decodeURIComponent(btn.dataset.start)
    );
  });
});
```

---

### CR-03: XSS — Achievement title and description from API injected via `innerHTML` in `logros.html`

**File:** `Frontend/logros.html:263,265`
**Issue:** `renderLogros()` builds `list.innerHTML` using template literals that embed `l.ach_title` and `l.ach_desc` directly from the API response. If the backend returns achievement text containing HTML (e.g., from a database populated with unsanitized data), it executes in the user's browser. The `ach_id` is also embedded in an `onclick` attribute string (`onclick="toggleLogro('${l.ach_id}')"`, line 272) — if IDs are non-numeric UUIDs or strings, a crafted ID could inject JS.

**Fix:** Either use `textContent` for each field by creating DOM nodes manually, or run all interpolated strings through an escape function before insertion:
```javascript
function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// In the template:
`<div class="logro-titulo">${escHtml(l.ach_title)}</div>
 <span class="logro-desc">${escHtml(l.ach_desc)}</span>`
```
For the `onclick` attribute, store `ach_id` in a `data-id` attribute and attach listeners after rendering, matching the pattern described in CR-02.

---

## Warnings

### WR-01: `fetchWithAuth` does not throw or return early after 401 — causes redirect race and state mutation

**File:** `Frontend/auth.js:61-65`, `Frontend/logros.html:222-224`
**Issue:** After a 401, `fetchWithAuth` calls `window.location.href = "login.html"` and then immediately `return response` — it does not throw. Navigation assignment in browsers is asynchronous; the JS event loop continues. Callers that check `if (!res.ok) throw new Error()` will enter their `catch` block and run error-handling code before the redirect completes. In `logros.html`, the `catch` block (line 222-224) explicitly reassigns `logro.status_completed = nuevoEstado` even on failure — so a 401 from a PATCH request silently flips the achievement state locally, shows a fake "+N pts" toast, and re-renders the list, all before the page navigates away.

**Fix in auth.js:** Throw after setting the redirect so callers' catch blocks can detect the auth failure and skip any state mutation:
```javascript
export async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    signOut();
    window.location.href = "login.html";
    throw new Error("Sesión expirada"); // stops caller execution
  }
  return response;
}
```
**Fix in logros.html:** The catch block should not mutate state — it should only show an error toast:
```javascript
} catch (err) {
  if (err.message !== "Sesión expirada") {
    showToast("Error al guardar el logro", true);
  }
}
```

---

### WR-02: Stale auth headers in FullCalendar events callback

**File:** `Frontend/calendario.html:303,349`
**Issue:** `currentHeaders` is assigned once at page load inside `requireAuth`. The FullCalendar `events` callback (which can be triggered multiple times as the user navigates months) uses the snapshot value of `currentHeaders` captured at initialization. Google OAuth access tokens have a 1-hour expiry. If a user leaves the calendar open for more than an hour and navigates to a new month, the calendar will fire the events callback with an expired token. The request will return 401, `fetchWithAuth` will redirect, but it is not obvious to the user why this happened.

**Fix:** Call `authHeaders()` freshly inside the FullCalendar callback each time it fires, so the token is read from `sessionStorage` at the moment of the request:
```javascript
events: async (info, successCallback, failureCallback) => {
  try {
    const headers = await authHeaders(); // not currentHeaders
    const res = await fetchWithAuth(`${API_BASE}/api/calendar/events?max_results=50`, { headers });
    ...
```
The same applies to `loadSchedulePanel` (line 603) and `sendMessage` (line 413) — all three currently read `currentHeaders` from the closed-over module-level variable.

---

### WR-03: Raw `fetch()` used for `/api/ranking/top` — inconsistent and fragile

**File:** `Frontend/ranking.html:152`
**Issue:** `loadTopRanking()` uses a bare `fetch()` instead of `fetchWithAuth()`, with the comment "no requiere auth." The backend confirms `/api/ranking/top` has no `Depends(get_current_user)`, so this is functionally correct today. However, if the endpoint is later secured (a likely future change given the pattern in all other endpoints), this call will silently fail with 401 and the error handler will show "No se pudo cargar el ranking" with no redirect, leaving the user stuck on a partially rendered page with no diagnostic.

**Fix:** Replace with `fetchWithAuth` for consistency, even without auth headers. If the endpoint is public, the wrapper still passes the call through unchanged when status != 401:
```javascript
const res = await fetchWithAuth(`${API_BASE}/api/ranking/top?limit=10`);
```

---

### WR-04: `loadMyRank` in `ranking.html` crashes if `data.data` is absent or `points` is undefined

**File:** `Frontend/ranking.html:143`
**Issue:** `data.points.toLocaleString()` is called without checking whether `data.points` exists. The backend returns `"points": points or 0`, so it should always be a number, but if the Redis key is missing or the response shape changes, `data.points` could be `null` or `undefined`, throwing a TypeError on `.toLocaleString()`.

**Fix:**
```javascript
document.getElementById("myPoints").textContent =
  `${(data.points ?? 0).toLocaleString()} pts`;
```

---

### WR-05: `requireAuth` callback receives `userInfo` from `sessionStorage` without verifying the token is still valid

**File:** `Frontend/auth.js:36-44`
**Issue:** `requireAuth` checks only that the `google_token` key exists in `sessionStorage`. It does not verify the token is unexpired before calling `callback(userInfo)`. This means pages load and attempt backend calls even if the stored token has already expired (e.g., user came back after a browser suspension). The backend will return 401 on the first real API call and `fetchWithAuth` will redirect — but there is a brief window where `requireAuth` reports "auth OK" and the page begins rendering with stale user data from `sessionStorage`, which could expose a flash of incorrect user info (name, email) from the stored snapshot.

**Fix (partial — without a server roundtrip):** At minimum, check that `user_info` in `sessionStorage` is parseable and non-empty before calling the callback. A more robust fix would be to validate the token expiry if GIS provides it in the response, or to have `requireAuth` make a lightweight backend ping before invoking the callback.

---

## Info

### IN-01: `API_BASE` hardcoded to `http://localhost:8000`

**File:** `Frontend/auth.js:12`
**Issue:** The API base URL is hardcoded as `http://` (not `https://`). For local development this is acceptable, but it means any deployment to a staging or production environment requires a code change. It also means all tokens sent via `Authorization` headers travel over plaintext HTTP in any non-localhost deployment.

**Fix:** Read from a build-time environment variable or a config file. As a minimal improvement, use a relative URL (`/api/...`) if frontend and backend are served from the same origin.

---

### IN-02: `GOOGLE_CLIENT_ID` hardcoded in `login.html`

**File:** `Frontend/login.html:111`
**Issue:** The OAuth client ID `486932937666-23r90cvcs0l5rib6imbk7h9r5r4miu2a.apps.googleusercontent.com` is committed in plain text. Client IDs are public-facing (they appear in OAuth redirect URLs), so this is not a secret — Google does not treat them as credentials. However, having it hardcoded makes rotating it in case of accidental scope expansion or domain change require a code change.

**Fix:** Move to a config file or environment variable at build time.

---

### IN-03: `handlePhotoChange` in `perfil.html` reads local file to DataURL but has no size limit

**File:** `Frontend/perfil.html:239-251`
**Issue:** A user can select any file (despite `accept="image/*"`) and it will be read into a DataURL. There is no check on file size before calling `readAsDataURL`. A 50 MB file would be read entirely into memory. The TODO comment notes the upload endpoint does not yet exist, so this is low priority, but the guard should be added before the upload is wired up.

**Fix (add before `reader.readAsDataURL`):**
```javascript
if (file.size > 5 * 1024 * 1024) {
  showToast("La imagen no puede superar 5 MB", true);
  return;
}
```

---

### IN-04: `appendPendingMsg` in `calendario.html` is defined but never called

**File:** `Frontend/calendario.html:517-523`
**Issue:** The function `appendPendingMsg` is defined but has no callers in the current codebase. Dead code.

**Fix:** Remove the function, or connect it to the appropriate flow if it is intended for a future feature.

---

_Reviewed: 2026-04-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
