# UI Contract: AuthErrorOverlay Component

## Component: `AuthErrorOverlay.qml`

### Required Properties (from parent)

| Property | Type | Binding Source | Description |
|---|---|---|---|
| `errorVisible` | bool | `chatController.authErrorVisible` | Whether the error overlay is shown |
| `errorCategory` | string | `chatController.authErrorCategory` | Error category enum value |
| `errorMessage` | string | `chatController.authErrorMessage` | Human-readable error text |
| `blockedReason` | string | `chatController.authErrorBlockedReason` | Block reason (BLOCKED only) |
| `blockedAt` | string | `chatController.authErrorBlockedAt` | Formatted block date (BLOCKED only) |
| `currentLevel` | int | `chatController.authErrorCurrentLevel` | Current access level (ACCESS_DENIED only) |
| `requiredLevel` | int | `chatController.authErrorRequiredLevel` | Required access level (ACCESS_DENIED only) |

### Signals (emitted to parent)

| Signal | Parameters | Description |
|---|---|---|
| `logoutClicked()` | — | User wants to clear credentials and return to login |
| `retryClicked()` | — | User wants to re-attempt authentication |
| `signinClicked()` | — | User wants to sign in with Discord (re-auth) |
| `goBackClicked()` | — | User wants to return to previous screen (permission only) |
| `closeAppClicked()` | — | User wants to exit the application (blocked only) |

### Visual States

| Category | Icon Color | Title Key | Body Key | Buttons |
|---|---|---|---|---|
| `BLOCKED` | danger (#E53935) | `error.auth.blocked.title` | `error.auth.blocked.body` | Logout, Close App |
| `ACCESS_DENIED` | warning (#FB8C00) | `error.auth.denied.title` | `error.auth.denied.body` | Retry, Logout |
| `REAUTH` | info (#1E88E5) | `error.auth.reauth.title` | `error.auth.reauth.body` | Sign in with Discord, Logout |
| `PERMISSION` | warning (#FB8C00) | `error.auth.permission.title` | `error.auth.permission.body` | Go Back, Logout |
| `NOT_FOUND` | danger (#E53935) | `error.auth.not_found.title` | `error.auth.not_found.body` | Logout |
| `UNKNOWN` | neutral (#78909C) | `error.auth.unknown.title` | `error.auth.unknown.body` | Retry, Logout |

### Layout Structure

```
┌─────────────────────────────────────────────┐
│                                             │
│           ⚠ [Category Icon]                │
│                                             │
│         [Title - category specific]         │
│                                             │
│    [Body text - category specific with      │
│     placeholder substitution]               │
│                                             │
│    ┌─────────────────────────────────┐      │
│    │ [Detail Panel - optional]       │      │
│    │ Reason: "Violação de regras"    │      │
│    │ Date: 30/06/2026 15:00          │      │
│    │ Level: 1 → Required: 2         │      │
│    └─────────────────────────────────┘      │
│                                             │
│    [Primary Button]  [Secondary Button]     │
│                                             │
│    [Help text / Contact support link]       │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Contract: Python → QML Properties

### New Properties on `ChatController`

```python
# All use the `changed` signal (existing) for notify

@Property(str, notify=changed)
def authErrorCategory(self) -> str:
    return self._auth_error_category  # "", "BLOCKED", "ACCESS_DENIED", "REAUTH", "PERMISSION", "NOT_FOUND", "UNKNOWN"

@Property(str, notify=changed)
def authErrorMessage(self) -> str:
    return self._auth_error_message

@Property(str, notify=changed)
def authErrorBlockedReason(self) -> str:
    return self._auth_error_blocked_reason

@Property(str, notify=changed)
def authErrorBlockedAt(self) -> str:
    return self._auth_error_blocked_at

@Property(int, notify=changed)
def authErrorCurrentLevel(self) -> int:
    return self._auth_error_current_level

@Property(int, notify=changed)
def authErrorRequiredLevel(self) -> int:
    return self._auth_error_required_level
```

### Modified Behavior in `_apply_result()` (kind == "auth-error")

```python
# Before (existing L5750-5770):
self._auth_error_visible = True
self._auth_denied = any(marker in payload_text for marker in denied_markers)
self._status = str(payload)

# After (replacement):
error_data = self._classify_auth_error(payload)
self._auth_error_visible = True
self._auth_error_category = error_data["category"]
self._auth_error_message = error_data["message"]
self._auth_error_blocked_reason = error_data.get("blockedReason", "")
self._auth_error_blocked_at = error_data.get("blockedAt", "")
self._auth_error_current_level = error_data.get("currentAccessLevel", 0)
self._auth_error_required_level = error_data.get("requiredAccessLevel", 0)
self._auth_denied = error_data["category"] == "ACCESS_DENIED"  # Backwards compat
self._status = error_data["message"]
```

---

## Contract: Translation Keys

### Key Format

All keys use `error.auth.{category}.{element}` namespace.

### Full Key List

```json
{
  "error.auth.blocked.title": "Conta bloqueada",
  "error.auth.blocked.body": "Sua conta GG foi bloqueada e você não pode acessar o aplicativo.",
  "error.auth.blocked.reason_label": "Motivo",
  "error.auth.blocked.date_label": "Bloqueado em",
  "error.auth.blocked.contact_support": "Entre em contato com a liderança do seu regimento para mais informações.",

  "error.auth.denied.title": "Acesso negado",
  "error.auth.denied.body": "Sua conta não possui permissão suficiente para acessar o aplicativo.",
  "error.auth.denied.level_info": "Seu nível de acesso ({current}) é inferior ao necessário ({required}).",
  "error.auth.denied.no_registration": "Você não possui permissões para criar uma conta no aplicativo.",
  "error.auth.denied.revoked": "Seu nível de permissão foi revogado.",

  "error.auth.reauth.title": "Sessão inválida",
  "error.auth.reauth.body": "Sua sessão expirou ou é inválida. Entre novamente com o Discord.",
  "error.auth.reauth.session_expired": "Sua sessão expirou. Faça login novamente.",
  "error.auth.reauth.token_invalid": "O token de autenticação é inválido.",
  "error.auth.reauth.account_not_found": "Sua conta de chat não foi encontrada.",
  "error.auth.reauth.discord_mismatch": "O token não corresponde à conta Discord esperada.",

  "error.auth.permission.title": "Permissão insuficiente",
  "error.auth.permission.body": "Você não possui permissões necessárias para esta ação.",
  "error.auth.permission.admin_only": "Esta funcionalidade é restrita a administradores.",

  "error.auth.not_found.title": "Conta não encontrada",
  "error.auth.not_found.body": "Sua conta não foi encontrada ou está inativa.",
  "error.auth.not_found.deactivated": "Sua conta foi desativada.",

  "error.auth.unknown.title": "Erro de autenticação",
  "error.auth.unknown.body": "Ocorreu um erro inesperado durante a autenticação.",

  "error.auth.btn.logout": "Sair da conta",
  "error.auth.btn.retry": "Tentar novamente",
  "error.auth.btn.signin_discord": "Entrar com Discord",
  "error.auth.btn.go_back": "Voltar",
  "error.auth.btn.close_app": "Fechar aplicativo",
  "error.auth.btn.contact_support": "Contatar suporte"
}
```
