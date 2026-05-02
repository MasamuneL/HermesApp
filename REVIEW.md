---
phase: google-oauth-calendar
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - Frontend/login.html
  - backend/app/routers/calendar.py
  - Frontend/calendario.html
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Code Review Report — Google Calendar Integration

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the three files implementing Google Calendar integration: the GIS OAuth login page, the FastAPI calendar router, and the frontend calendar page. The refactor to offload blocking Google API calls to a thread executor is correct in intent but uses the deprecated `asyncio.get_event_loop()` call (should be `get_running_loop()`). The most important security finding is an XSS vulnerability in the event confirmation card inside `calendario.html`: user-controlled data from the chat assistant's JSON response is injected into `innerHTML` without escaping. Auth token handling and the `include_granted_scopes: false` change are sound. Error handling has several gaps that would surface as confusing 400 responses instead of correct 4xx codes.

---

## Critical Issues

### CR-01: XSS via unescaped event data injected into innerHTML

**File:** `Frontend/calendario.html:503-513`

**Issue:** `showEventConfirmation(evento)` builds an HTML string with template literals and sets it via `div.innerHTML`. The fields `evento.titulo`, `evento.title`, `evento.hora`, and `evento.descripcion` come directly from `JSON.parse(data.response)` at line 440 — i.e., they are strings returned by the Gemini backend. If the LLM response or an intercepted backend response contains `<script>` tags or event-handler attributes in those fields, they execute in the user's browser.

`appendMsg()` at line 519 correctly calls `escapeHtml()`, but `showEventConfirmation()` does not.

```javascript
// CURRENT (vulnerable)
div.innerHTML = `
  Encontré este evento. ¿Lo agendo?
  <div class="event-card-msg">
    <div class="ec-title">📅 ${evento.titulo || evento.title}</div>
    <div class="ec-detail">🕐 ${formatFecha(evento.fecha)} a las ${evento.hora}</div>
    ${evento.descripcion ? `<div class="ec-detail">📝 ${evento.descripcion}</div>` : ""}
    ...
  </div>`;

// FIX — escape every user-controlled field
div.innerHTML = `
  Encontré este evento. ¿Lo agendo?
  <div class="event-card-msg">
    <div class="ec-title">📅 ${escapeHtml(evento.titulo || evento.title || "")}</div>
    <div class="ec-detail">🕐 ${escapeHtml(formatFecha(evento.fecha))} a las ${escapeHtml(evento.hora || "")}</div>
    ${evento.descripcion ? `<div class="ec-detail">📝 ${escapeHtml(evento.descripcion)}</div>` : ""}
    ...
  </div>`;
```

---

## Warnings

### WR-01: `asyncio.get_event_loop()` is deprecated in async context — use `get_running_loop()`

**File:** `backend/app/routers/calendar.py:50` and `:101`

**Issue:** Inside an `async` FastAPI handler, there is always an active running event loop. `asyncio.get_event_loop()` is deprecated in Python 3.10+ when called from a coroutine; it emits a `DeprecationWarning` and may return the wrong loop in edge cases (e.g., if the handler runs inside a sub-thread). The correct call is `asyncio.get_running_loop()`, which raises `RuntimeError` if there is no running loop instead of silently creating a new one.

```python
# CURRENT (deprecated)
loop = asyncio.get_event_loop()
items = await loop.run_in_executor(None, _fetch_events_sync, ...)

# FIX
loop = asyncio.get_running_loop()
items = await loop.run_in_executor(None, _fetch_events_sync, ...)
```

Apply the same change at line 101 inside `create_event`.

---

### WR-02: Bare `except Exception` swallows all errors and returns misleading 400

**File:** `backend/app/routers/calendar.py:74-76` and `:119-120`

**Issue:** The fallback `except Exception` in both handlers converts every unhandled error — including network failures toward Google's API, `KeyError` on the response dict, Pydantic validation errors, and executor-related exceptions — into a generic HTTP 400. This is incorrect:

- Network / timeout errors from the executor should be 502 (Bad Gateway) or 503.
- `KeyError` when accessing `item["start"]` or `created["start"]` is a server-side bug and should surface as 500 (or be guarded).
- Logging `str(e)` leaks internal error details to the API client.

```python
# FIX — tighten the fallback
except HttpError as e:
    logger.error("Google Calendar HTTP error: %s %s", e.status_code, e.reason)
    raise HTTPException(status_code=e.status_code, detail="Error de Google Calendar")
except (KeyError, ValueError) as e:
    logger.exception("Unexpected data shape from Google Calendar")
    raise HTTPException(status_code=500, detail="Respuesta inesperada de Google Calendar")
except Exception as e:
    logger.exception("Unexpected error in calendar handler")
    raise HTTPException(status_code=502, detail="No se pudo comunicar con Google Calendar")
```

---

### WR-03: `start` or `end` can be `None` — unguarded access crashes silently

**File:** `backend/app/routers/calendar.py:57-58` and `:109-110`

**Issue:** The expression `item["start"].get("dateTime", item["start"].get("date"))` returns `None` if both `dateTime` and `date` are absent from the Google Calendar event object (which can happen for cancelled or malformed events). `CalendarEventResponse` receives `None` for `start` or `end`. If those fields are typed as non-optional in the Pydantic schema, Pydantic will raise a `ValidationError` caught by the broad `except Exception` at line 74 and returned as HTTP 400. If they are optional, `None` silently propagates to the frontend where `new Date(null)` causes `Invalid Date` rendering errors.

```python
# FIX — add a guard
start = item["start"].get("dateTime") or item["start"].get("date")
end   = item["end"].get("dateTime")   or item["end"].get("date")
if not start or not end:
    logger.warning("Skipping event with missing start/end: %s", item.get("id"))
    continue
```

---

### WR-04: `confirmEvent` builds ISO datetime strings with no validation — silently sends wrong times when `hora_fin` is absent

**File:** `Frontend/calendario.html:469`

**Issue:** When `pendingEvento.hora_fin` is missing, the code falls back to `pendingEvento.hora` for the end time, constructing a zero-duration event (`start == end`). Google Calendar API accepts this without error, but it creates an event that has no visible block on the calendar. There is no warning to the user and no check that the constructed datetime strings are valid ISO 8601 before sending them.

```javascript
// CURRENT
end: `${pendingEvento.fecha}T${pendingEvento.hora_fin || pendingEvento.hora}:00`,

// FIX — show the end time in the confirmation card and validate before sending
const horaFin = pendingEvento.hora_fin || pendingEvento.hora;
// Warn the user in showEventConfirmation if hora_fin is absent
// Before POST, validate:
if (!pendingEvento.fecha || !pendingEvento.hora) {
  appendMsg("El asistente no pudo determinar la fecha u hora del evento.", "bot");
  pendingEvento = null;
  return;
}
```

---

### WR-05: `requireAuth` does not verify token validity — a token present in sessionStorage but already expired will reach the backend and receive a 401

**File:** `Frontend/auth.js:36-44`  
(consumed by `calendario.html:320`)

**Issue:** `requireAuth` only checks that the string `google_token` is non-null in sessionStorage. An expired Google OAuth access token (lifetime: 1 hour) passes this check, and every subsequent `fetchWithAuth` call will receive a 401 until the user refreshes the page — at which point they are redirected to `login.html`. `fetchWithAuth` does handle 401 by redirecting, but the user experiences a broken calendar load (FullCalendar renders with no events and no visible error) rather than a proactive re-auth prompt.

This is an architectural gap rather than a straightforward fix, but the minimum mitigation is to store the token expiry time during login and check it in `requireAuth`:

```javascript
// In login.html — after receiving the token response
sessionStorage.setItem("google_token_exp", String(Date.now() + (resp.expires_in - 60) * 1000));

// In auth.js — requireAuth
export function requireAuth(callback) {
  const token = getToken();
  const exp   = Number(sessionStorage.getItem("google_token_exp") || 0);
  if (!token || Date.now() > exp) {
    signOut();
    window.location.href = "login.html";
    return;
  }
  const userInfo = JSON.parse(sessionStorage.getItem("user_info") || "{}");
  callback(userInfo);
}
```

---

## Info

### IN-01: Hardcoded Google OAuth Client ID in login.html

**File:** `Frontend/login.html:111`

**Issue:** The OAuth client ID `486932937666-23r90cvcs0l5rib6imbk7h9r5r4miu2a.apps.googleusercontent.com` is hardcoded. While client IDs for browser-side OAuth flows are not secret (they are visible to anyone who views the page source), hardcoding them makes it harder to rotate or switch between environments (dev/staging/prod). Consider externalizing to a config file or build-time variable.

---

### IN-02: `API_BASE` hardcoded to `localhost:8000` in both login.html and auth.js

**File:** `Frontend/login.html:110`, `Frontend/auth.js:12`

**Issue:** Both files hardcode `http://localhost:8000`. This works for local development but will break silently in any deployed environment. Centralizing this in a single config or using a relative URL (if frontend and backend are served from the same origin) would reduce the maintenance surface.

---

### IN-03: `include_granted_scopes: false` is correct but the rationale should be documented

**File:** `Frontend/login.html:135`

**Issue:** Setting `include_granted_scopes: false` disables Google's incremental authorization feature, ensuring that each token request explicitly asks for the full `SCOPES` list rather than inheriting whatever was granted in previous sessions. This is the correct setting for this app since Calendar scope is always required. However, the comment above `initTokenClient` does not explain why this flag was set to `false`. A future developer may assume it is a default no-op and change it, silently breaking Calendar access for users who previously only granted basic profile scopes.

```javascript
// SUGGESTED COMMENT
// include_granted_scopes: false prevents GIS from merging this request
// with previously granted scopes. Without this, a user who once logged in
// with only openid/email would not be prompted to grant Calendar access
// on re-login, and backend Calendar calls would fail with 403.
include_granted_scopes: false,
```

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
