# Data Model: Auth Error Screens

## Entities

### AuthErrorCategory (Enum)

Classifies backend auth errors into UI-actionable categories.

| Value | Description | Recovery Actions |
|---|---|---|
| `BLOCKED` | GG account is blocked (403 + blockedReason) | Logout, Close App |
| `ACCESS_DENIED` | Insufficient access level or no panel permissions (403) | Logout, Retry |
| `REAUTH` | Invalid token, expired session, or invalid auto-login key (401) | Sign in with Discord, Logout |
| `PERMISSION` | Insufficient role for admin/restricted action (403) | Go Back, Logout |
| `NOT_FOUND` | User account not found or deactivated (404/403) | Logout, Contact Support |
| `UNKNOWN` | Unrecognized error format | Logout, Retry |

### AuthErrorData (Value Object)

Structured data extracted from the backend error response, exposed to QML as properties.

| Field | Type | Source | Used By |
|---|---|---|---|
| `category` | string | Classified from status + message | All screens |
| `message` | string | Raw error message text | All screens (fallback body text) |
| `httpStatus` | int | HTTP response status code | Classification logic |
| `blockedReason` | string | `response.blockedReason` | Blocked screen |
| `blockedAt` | string | `response.blockedAt` (ISO datetime) | Blocked screen (formatted) |
| `currentAccessLevel` | int | `response.accessLevel` | Access Denied screen |
| `requiredAccessLevel` | int | `response.panelAccess.requiredAccessLevel` | Access Denied screen |
| `reasonCode` | string | `response.reason` (USER_NOT_REGISTERED, ACCESS_DENIED, BLOCKED) | Classification refinement |
| `authFlow` | string | `response.authFlow` | Diagnostic info |

### Classification Rules (State Transition)

```
Backend Response → classify_auth_error() → AuthErrorCategory + AuthErrorData
```

**Priority order** (first match wins):

```
1. status=403 AND ("bloqueada" OR "blocked" OR blockedReason present)
   → BLOCKED

2. status=403 AND ("acesso negado" OR "access denied" OR "acceso denegado" 
   OR "acces refuse" OR "permissão foi revogado" OR "access level")
   → ACCESS_DENIED

3. status=401 AND ("auto-login" OR "token" OR "sessão expirada" OR "session expired"
   OR "nao encontrado" OR "not found")
   → REAUTH

4. status=403 AND ("permissao insuficiente" OR "apenas administradores"
   OR "insufficient permission" OR "administrators only")
   → PERMISSION

5. status=404 OR (status=403 AND ("desativada" OR "deactivated"))
   → NOT_FOUND

6. Any other error
   → UNKNOWN
```

**Note on priority**: BLOCKED is checked before ACCESS_DENIED because a blocked account response may also contain "acesso negado" in its text. The presence of `blockedReason` or "bloqueada"/"blocked" keywords uniquely identifies the blocked state.

### Screen → Button Mapping

| Category | Primary Button | Secondary Button | Tertiary Button |
|---|---|---|---|
| BLOCKED | Logout | Close App | — |
| ACCESS_DENIED | Retry | Logout | — |
| REAUTH | Sign in with Discord | Logout | — |
| PERMISSION | Go Back | Logout | — |
| NOT_FOUND | Logout | — | — |
| UNKNOWN | Retry | Logout | — |

### State Transitions

```
Any Screen → Logout click → Credentials cleared → Discord Login Screen
Any Screen → Retry/Sign in click → Auth in flight → Success OR Error Screen
PERMISSION Screen → Go Back click → Previous app state (overlay hidden)
BLOCKED Screen → Close App click → Application exits
```

## Relationship to Existing Model

### Existing Properties (preserved, re-semanticized)

| Property | Current Use | New Use |
|---|---|---|
| `authErrorVisible` | Binary: any auth error | Still True when any auth error — category provides detail |
| `authDenied` | Binary: access denied | Deprecated in UI logic — replaced by `authErrorCategory == "ACCESS_DENIED"` |
| `profileGateVisible` | Login overlay visibility | Unchanged — error overlay shown inside login overlay |

### New Properties (added to ChatController)

| Property | Type | Description |
|---|---|---|
| `authErrorCategory` | string | One of: BLOCKED, ACCESS_DENIED, REAUTH, PERMISSION, NOT_FOUND, UNKNOWN, "" |
| `authErrorMessage` | string | Human-readable error message for display |
| `authErrorBlockedReason` | string | Block reason (only set for BLOCKED) |
| `authErrorBlockedAt` | string | Block date/time formatted (only set for BLOCKED) |
| `authErrorCurrentLevel` | int | Current access level (only set for ACCESS_DENIED) |
| `authErrorRequiredLevel` | int | Required access level (only set for ACCESS_DENIED) |
