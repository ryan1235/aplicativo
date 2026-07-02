# Feature Specification: Auth Error Screens

**Feature Branch**: `001-auth-error-screens`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Verificar e criar telas dedicadas para todos os erros de login/auth do backend, com formas de sair da conta e tentar novamente. Atualmente, os erros são tratados inline no overlay de login ou via dialog genérico, sem telas dedicadas por tipo de erro."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Blocked Account Screen (Priority: P1)

A user whose GG account has been blocked (403 with `blockedReason` and `blockedAt`) sees a dedicated full-screen error state explaining that their account is blocked, showing the reason and the date/time of the block. The user can choose to **log out** (clearing credentials) to switch accounts, or **close the app**.

**Why this priority**: A blocked user is currently shown a generic "access denied" state with no specific explanation. This is the most critical error to surface clearly because the user cannot recover without admin intervention; showing them actionable information (reason, date, contact support) reduces confusion and support tickets.

**Independent Test**: Block a test account via backend, launch the app, and verify the blocked screen appears with correct reason and date. Verify the logout button clears credentials and returns to the Discord login screen.

**Acceptance Scenarios**:

1. **Given** a user with a blocked GG account (403, `blockedReason: "Violação de regras"`, `blockedAt: "2026-06-30T15:00:00Z"`), **When** the user attempts to authenticate (via auto-login or Discord OAuth), **Then** the app shows the Blocked Account Screen with the block reason, formatted block date, a logout button, and a "contact support" message.
2. **Given** the Blocked Account Screen is displayed, **When** the user clicks "Log out", **Then** secure credentials are cleared, the app returns to the Discord login screen, and the user can attempt to log in with a different Discord account.
3. **Given** the Blocked Account Screen is displayed, **When** the user clicks "Close app", **Then** the application closes gracefully.

---

### User Story 2 - Access Denied Screen (Priority: P1)

A user whose access level is insufficient (403, various "Acesso negado" variants) sees a dedicated Access Denied Screen that explains their current access level versus the required level, and whether they lack panel permissions or app registration. The user can **log out** to switch accounts or **retry** (in case permissions were just updated).

**Why this priority**: Access denial is the second most common auth error. Users need to understand *why* they cannot access the app and what action to take (contact admin for access upgrade, or retry if permissions were just changed).

**Independent Test**: Set a test account with `accessLevel < 2`, attempt login, verify the Access Denied Screen shows current vs required level. Change access level to >= 2, click retry, verify successful login.

**Acceptance Scenarios**:

1. **Given** a user with `accessLevel: 1` (required: 2), **When** they authenticate, **Then** the Access Denied Screen shows "Your access level (1) is below the required level (2)" with the specific denial reason, a retry button, and a logout button.
2. **Given** a user without a GG account attempting OAuth registration but lacking external permissions, **When** they authenticate, **Then** the Access Denied Screen shows a message explaining they don't have panel permissions to create an account, with logout and retry buttons.
3. **Given** a user whose access level was revoked after registration (auto-login flow), **When** auto-login runs, **Then** the Access Denied Screen shows that permissions were revoked, credentials are cleared, and logout/retry buttons are available.
4. **Given** the Access Denied Screen with retry button, **When** the user clicks "Retry" after their access was updated server-side, **Then** authentication re-runs and succeeds, taking them to the app.

---

### User Story 3 - Reauthentication Screen (Priority: P1)

A user whose token is invalid, session is expired, or auto-login key is invalid sees a Reauthentication Screen that explains the session issue and prompts them to sign in again with Discord. The user can **log out** (to fully clear credentials and start fresh) or **sign in with Discord** (to re-authenticate).

**Why this priority**: Token/session issues are common during normal usage (token expiry, server-side revocation, key rotation). Users need a clear path to re-authenticate without confusion about what went wrong.

**Independent Test**: Invalidate a user's auto-login key server-side, launch the app, verify the Reauth Screen appears with appropriate message. Click "Sign in with Discord" and verify successful re-authentication.

**Acceptance Scenarios**:

1. **Given** a user with an invalid auto-login key (401: "Chave de auto-login invalida"), **When** auto-login runs, **Then** the Reauth Screen shows "Your login session is invalid. Please sign in again.", stored credentials are cleared, and a "Sign in with Discord" button is shown.
2. **Given** a user with a missing or invalid chat token (401), **When** attempting to use chat features, **Then** the Reauth Screen shows the token error and offers sign-in and logout options.
3. **Given** a user whose chat account was deleted but token is still valid (401: "Usuario do chat nao encontrado"), **When** they attempt to use the app, **Then** the Reauth Screen shows "Your chat account was not found" with sign-in and logout options.
4. **Given** a user with an expired or revoked refresh token (401: "Sessão expirada ou inválida"), **When** they attempt any authenticated action, **Then** the Reauth Screen shows "Your session has expired. Please sign in again." with sign-in and logout options.
5. **Given** a user whose Discord token doesn't match (403: "Token inválido para este usuário Discord" or "Token invalido para este Discord"), **When** they attempt to authenticate, **Then** the Reauth Screen shows a Discord mismatch error with sign-in and logout options.

---

### User Story 4 - Permission Screen (Priority: P2)

A user who tries to access an admin or restricted feature without sufficient permissions sees a Permission Screen explaining the required role. The user can **go back** to the previous screen or **log out**.

**Why this priority**: Permission errors affect fewer users (admins only) and happen mid-session rather than at login. They are important but less critical than login-blocking errors.

**Independent Test**: Log in with a non-admin account, attempt to access the admin panel, verify the Permission Screen appears with appropriate message. Click "Go back" and verify the user returns to the previous screen.

**Acceptance Scenarios**:

1. **Given** a non-admin user, **When** they attempt to access a chat admin route (403: "Permissao insuficiente"), **Then** the Permission Screen shows "You don't have sufficient permissions for this action" with a "Go back" button.
2. **Given** a non-admin user, **When** they attempt to access the classic admin panel (403: "Acesso negado. Apenas administradores."), **Then** the Permission Screen shows an admin-only message with "Go back" and "Log out" buttons.

---

### User Story 5 - Not Found Screen (Priority: P2)

A user whose profile, chat account, or requested resource cannot be found (404) sees a Not Found Screen with a clear explanation and recovery options. The user can **retry**, **log out**, or **go back**.

**Why this priority**: Not found errors are less common and typically indicate data inconsistencies. They still need proper handling to prevent the user from being stuck.

**Independent Test**: Simulate a 404 response from `/auth/me`, verify the Not Found Screen appears. Click retry and verify re-fetch.

**Acceptance Scenarios**:

1. **Given** a user whose account does not exist or is not active (404: "Usuário não encontrado" from `/auth/me`), **When** the app fetches their profile, **Then** the Not Found Screen shows "Your account was not found or is inactive" with retry, logout, and "contact support" options.
2. **Given** a deactivated user account (403: "Conta desativada"), **When** they attempt classic panel login, **Then** the Not Found Screen shows "Your account has been deactivated" with a logout button and contact support guidance.

---

### Edge Cases

- What happens when the backend returns an unrecognized error code or message that doesn't match any known pattern? → The app shows a generic error fallback with the raw error message, retry button, and logout button.
- What happens when the user is offline and the auth request fails with a network error? → The existing network-unavailable handling takes precedence; auth error screens are for server-returned errors only.
- What happens when multiple error conditions apply simultaneously (e.g., blocked + expired token)? → The first error received from the backend determines the screen shown. Backend errors have natural priority (blocked → denied → auth → permission).
- What happens when the user clicks retry but the error persists? → The retry button respects the existing 30-second cooldown timer. The screen remains visible with the same error state until a different response is received.
- What happens after minimize, tray restore, close-to-background, restart, and app update flows? → Error screen state persists through minimize/tray but is re-evaluated on restart or app update (fresh auth attempt).
- What happens when the app is running and the user's account is blocked mid-session? → The error screen appears on the next API call that returns the blocked status, not proactively.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify incoming auth errors into one of five categories: Blocked, Access Denied, Reauthentication, Permission, and Not Found, based on HTTP status code and error message content.
- **FR-002**: System MUST display a dedicated full-screen error state for each error category, replacing the current generic inline error handling in the login overlay.
- **FR-003**: Every error screen MUST include a "Log out" button that clears all stored credentials (auto-login key, tokens) and returns to the Discord login screen.
- **FR-004**: Error screens for recoverable errors (Access Denied, Reauthentication, Not Found) MUST include a "Retry" or "Sign in with Discord" button.
- **FR-005**: The Blocked Account Screen MUST display `blockedReason` and a human-readable formatted `blockedAt` date/time.
- **FR-006**: The Access Denied Screen MUST display the user's current `accessLevel` and the required `accessLevel` when available from the response fields.
- **FR-007**: The Reauthentication Screen MUST automatically clear stored credentials (`felb_credentials.bin`) when the error indicates the stored key/token is invalid.
- **FR-008**: The Permission Screen MUST include a "Go back" action that returns the user to the previous screen without logging out.
- **FR-009**: System MUST show a generic error fallback screen with the raw error message, retry, and logout when the error doesn't match any known category.
- **FR-010**: All error screens MUST block interaction with underlying app content (z-order above all other content, matching current overlay behavior).
- **FR-011**: The retry button MUST respect the existing 30-second cooldown timer and show remaining time when in cooldown.
- **FR-012**: System MUST map the following backend response fields to display fields: `blockedReason`, `blockedAt`, `accessLevel`, `authFlow`, `reauthRequired`, `panelAccess.canLoginPanel`, `panelAccess.requiredAccessLevel`, `reason` (with values `USER_NOT_REGISTERED`, `ACCESS_DENIED`, `BLOCKED`).

### Local Data & Settings *(include when feature persists data)*

- **Data Location**: Credential storage in `felb_credentials.bin` via DPAPI (existing `secure_store.py`). No new persistent data required.
- **Migration/Compatibility**: No changes to existing settings structure. Error classification is derived from backend responses, not stored locally.
- **Failure Handling**: If credential clearing fails during logout, log the error and still reset the in-memory auth state to allow re-login.

### Integration & Offline Behavior *(include when feature touches Steam/Foxhole/API/update flows)*

- **Unavailable Dependency**: When the network is unavailable, the existing network error handling takes precedence over auth error screens. Auth error screens only activate for server-returned error responses.
- **Timeout/Retry Behavior**: Retry respects the existing 30-second cooldown. The retry button shows a countdown ("Retry in Xs") during cooldown. After cooldown, retry attempts the appropriate auth flow (auto-login or Discord OAuth).
- **Safe Fallback**: If error classification fails (unrecognized error format), the generic fallback screen displays the raw error text with retry and logout options.

### Localization & User-Facing Text *(mandatory for UI changes)*

- **User-Facing Strings**: All error screen titles, descriptions, button labels, help text, and status messages must be added to the translation system.
- **Translation Catalogs**: pt/en/es/fr entries must be added for:
  - Blocked screen: title, description template (with reason/date placeholders), contact support text
  - Access Denied screen: title, description template (with level placeholders), permission explanation
  - Reauth screen: title, session expired text, token invalid text, account not found text
  - Permission screen: title, insufficient permission text, admin-only text
  - Not Found screen: title, account not found text, account deactivated text
  - Common: logout button, retry button, retry countdown, go back button, close app button, sign in with Discord button, generic error title/description

### Key Entities *(include if feature involves data)*

- **AuthError**: Represents a classified authentication error with properties: category (blocked/denied/reauth/permission/notfound/unknown), httpStatus, message, blockedReason, blockedAt, currentAccessLevel, requiredAccessLevel, reason code, authFlow.
- **ErrorScreenState**: Represents the current error screen visibility and category, driving which QML error component is shown. Properties: visible, category, errorData, retryCooldownRemaining.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every one of the 15 documented backend auth errors maps to a specific error screen category and displays a meaningful, localized message (not a generic fallback).
- **SC-002**: Every error screen provides at least one recovery action (logout, retry, sign in, go back, or close app) — no error state leaves the user stuck with no way out.
- **SC-003**: The logout action from any error screen successfully clears all stored credentials and returns to the Discord login screen within 2 seconds.
- **SC-004**: The retry action respects the 30-second cooldown and, when permissions are updated server-side, successfully recovers within one retry attempt.
- **SC-005**: All error screen strings appear in all four supported language catalogs (pt, en, es, fr) with correct placeholder substitution.
- **SC-006**: Error screens block all underlying app interaction (no click-through, no keyboard shortcuts reaching below) matching current overlay z-order behavior.

## Assumptions

- The app's existing Discord OAuth and auto-login auth flows remain the primary auth mechanisms; this feature adds error handling screens on top, not new auth flows.
- The backend API contract for error responses (status codes, message strings, response body fields) remains stable and matches the documented error list.
- Error classification is done client-side based on HTTP status and response content; no new backend endpoints are required.
- The existing 30-second retry cooldown timer is the correct interval and does not need adjustment.
- The admin panel access denied errors (currently handled via `startupDialog`) will be migrated to use the new Permission Screen component for consistency.
- DPAPI credential storage (`secure_store.py`) behavior is unchanged; error screens only trigger the existing `_clear_secure_login_credentials()` flow.
- Error screens are full-screen overlays in the QML layer, following the same pattern as the existing `discordLoginOverlay`.
