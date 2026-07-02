# Research: Auth Error Screens

## R1: Error Classification Strategy

**Decision**: Client-side classification via HTTP status code + error message pattern matching in `_apply_result()` (qt_controllers.py L5750-5770).

**Rationale**: The backend already returns distinct status codes (401, 403, 404) and descriptive Portuguese messages. No new backend endpoints needed. The existing `denied_markers` pattern (L5760-5768) proves this approach works — we extend it to cover all 5 categories.

**Alternatives considered**:
- Backend sends structured error codes (e.g., `errorType: "BLOCKED"`) → requires backend changes, out of scope
- Single generic error screen with different text → loses the UX benefit of tailored recovery actions per category

**Classification rules** (evaluated in order — first match wins):

| Category | HTTP Status | Message markers |
|---|---|---|
| BLOCKED | 403 | `"bloqueada"`, `"blocked"`, `"blockedReason"` |
| ACCESS_DENIED | 403 | `"acesso negado"`, `"access denied"`, `"acceso denegado"`, `"acces refuse"`, `"permissão foi revogado"`, `"access level"` |
| REAUTH | 401 | `"auto-login invalida"`, `"token invalido"`, `"token inválido"`, `"sessão expirada"`, `"session expired"`, `"nao encontrado"` (user context), `"not found"` (user context) |
| PERMISSION | 403 | `"permissao insuficiente"`, `"apenas administradores"`, `"insufficient permission"`, `"administrators only"` |
| NOT_FOUND | 404 | `"não encontrado"`, `"not found"`, `"desativada"`, `"deactivated"` |
| UNKNOWN | any | Fallback for unrecognized errors |

---

## R2: Error Data Extraction from Backend Responses

**Decision**: Parse the raw error payload (currently stored as `self._status = str(payload)`) to extract structured fields when available.

**Rationale**: Some backend errors return JSON with fields like `blockedReason`, `blockedAt`, `accessLevel`, `reason`. The current code stringifies the entire payload. We need to preserve the structured data for display.

**Implementation**: In the worker thread error handler (L5232-5257), when catching the error, attempt to parse the response body as JSON to extract known fields before falling back to the string message.

**Fields to extract**:
- `blockedReason` → display on blocked screen
- `blockedAt` → format as localized date on blocked screen
- `accessLevel` → display current level on access denied screen
- `requiredAccessLevel` (from `panelAccess.requiredAccessLevel`) → display required level
- `reason` → machine-readable reason code (USER_NOT_REGISTERED, ACCESS_DENIED, BLOCKED)

---

## R3: QML UI Architecture for Error Screens

**Decision**: Create a single `AuthErrorOverlay.qml` component that replaces the error states inside `discordLoginOverlay`, not 5 separate pages.

**Rationale**:
- The existing `discordLoginOverlay` already handles the full-screen blocking overlay pattern (z:9999, anchors.fill, gate logic)
- Error screens are states within the auth flow, not separate navigable pages
- A single component with internal state management keeps the architecture simple
- All error screens share common elements: icon, title, body, buttons — just different content

**Alternatives considered**:
- 5 separate QML files (BlockedScreen.qml, AccessDeniedScreen.qml, etc.) → too much duplication, harder to maintain consistent layout
- Inline all variants in Main.qml → Main.qml is already 2000+ lines, adding complexity there is undesirable

**Component structure**:
```
AuthErrorOverlay.qml
├── Error icon/illustration (category-specific color)
├── Title text (category-specific)
├── Body text (category-specific, with data placeholders)
├── Detail section (optional: reason, date, access level)
├── Action buttons (category-specific combination)
└── Help text (optional)
```

---

## R4: Retry Cooldown Behavior

**Decision**: Keep the existing 30-second cooldown for auto-connect but allow immediate manual retry from error screens.

**Rationale**: The current code already does this — `connectWithDiscord()` (L5184) resets `_auth_retry_after = 0.0` before calling `_connect_with_discord()`. The cooldown only prevents the auto-connect timer from spamming. Manual retries should always be responsive.

**UI behavior**: The retry button on error screens calls `connectWithDiscord()` directly, which resets the cooldown. No countdown timer needed on the button since manual clicks bypass cooldown.

---

## R5: Admin Panel Error Migration

**Decision**: Keep the `startupDialog` for admin panel errors but translate the hardcoded Portuguese strings.

**Rationale**: Admin panel errors (L1531-1669) happen mid-session when the user explicitly tries to open the admin panel. They are modal dialogs that don't block the entire app — only the admin panel attempt. This is fundamentally different from login-blocking auth errors which prevent all app usage.

**Changes needed**:
- Replace 3 hardcoded Portuguese strings in `openAdminPanel()` / `_on_panel_access_result()` with i18n calls
- Add corresponding translation keys for pt/en/es/fr
- Keep existing retry mechanism (`retryAdminPanelAccess()`)

---

## R6: Credential Clearing on Error Screens

**Decision**: Auto-clear credentials only for REAUTH category. For all others, credentials persist until explicit logout.

**Rationale**:
- BLOCKED: User might want to retry after admin unblocks — but the stored key is for a blocked account, so clearing is debatable. Keep credentials so if admin unblocks, auto-login will work on retry.
- ACCESS_DENIED: Permissions might be updated server-side. Keep credentials for retry.
- REAUTH: The stored key/token IS the problem. Must clear to allow fresh auth.
- PERMISSION: Mid-session error, user is already authenticated.
- NOT_FOUND: Account doesn't exist. Clear credentials to force fresh login.

**Current behavior preserved**: The reauth markers at L5243 already clear credentials for auto-login failures. We extend this to also clear for NOT_FOUND.

---

## R7: Translation Key Structure

**Decision**: Namespace all new keys under `error.auth.*` to distinguish from existing `loading.*` keys.

**Key naming convention**:
```
error.auth.blocked.title
error.auth.blocked.body
error.auth.blocked.reason_label
error.auth.blocked.date_label
error.auth.blocked.contact_support

error.auth.denied.title
error.auth.denied.body
error.auth.denied.level_info
error.auth.denied.no_registration

error.auth.reauth.title
error.auth.reauth.body
error.auth.reauth.session_expired
error.auth.reauth.token_invalid
error.auth.reauth.account_not_found

error.auth.permission.title
error.auth.permission.body
error.auth.permission.admin_only

error.auth.not_found.title
error.auth.not_found.body
error.auth.not_found.deactivated

error.auth.unknown.title
error.auth.unknown.body

error.auth.btn.logout
error.auth.btn.retry
error.auth.btn.signin_discord
error.auth.btn.go_back
error.auth.btn.close_app
error.auth.btn.contact_support
```

**Rationale**: Keeps auth error strings separate from loading flow strings. The `loading.*` keys remain for the normal login overlay states (awaiting Discord, loading profile, etc.).
