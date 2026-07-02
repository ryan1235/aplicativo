# Quickstart: Auth Error Screens Validation

## Prerequisites

- Windows machine with Python 3.x and PySide6 installed
- GG Coalition app runnable locally via `python felb_app.py`
- Backend access to create/modify test accounts
- Discord OAuth configured in `.env`

## Validation Scenarios

### Scenario 1: Blocked Account Screen

**Setup**: Block a test GG account via backend admin (set `blockedReason` and `blockedAt`).

**Steps**:
1. Launch app with the blocked account's stored credentials
2. Wait for auto-login attempt

**Expected**:
- Full-screen overlay appears with danger-colored styling
- Title shows translated "Conta bloqueada" / "Account blocked"
- Body shows the block reason and formatted block date
- Two buttons visible: "Sair da conta" (Logout) and "Fechar aplicativo" (Close App)
- Clicking "Sair da conta" clears credentials and shows Discord login screen
- Clicking "Fechar aplicativo" closes the app

---

### Scenario 2: Access Denied Screen

**Setup**: Set a test account with `accessLevel: 1` (required: 2).

**Steps**:
1. Launch app, complete Discord OAuth
2. Backend returns 403 with "Acesso negado" and access level info

**Expected**:
- Full-screen overlay with warning-colored styling
- Title shows "Acesso negado" / "Access denied"
- Body shows current vs required access level
- Two buttons: "Tentar novamente" (Retry) and "Sair da conta" (Logout)
- Update access level to 2 on backend, click Retry → app proceeds to profile loading

---

### Scenario 3: Reauthentication Screen

**Setup**: Invalidate a test account's auto-login key in backend.

**Steps**:
1. Launch app with stored (now-invalid) auto-login key
2. Auto-login fails with 401

**Expected**:
- Full-screen overlay with info-colored styling
- Title shows "Sessão inválida" / "Invalid session"
- Stored credentials are automatically cleared
- Two buttons: "Entrar com Discord" (Sign in with Discord) and "Sair da conta" (Logout)
- Clicking "Entrar com Discord" starts OAuth flow

---

### Scenario 4: Permission Screen

**Setup**: Log in with a non-admin account.

**Steps**:
1. Successfully authenticate and load profile
2. Attempt to access admin panel

**Expected**:
- Modal dialog with warning styling (startupDialog, not full-screen overlay)
- Title shows translated "Acesso Negado ao Painel" (now via i18n, not hardcoded)
- Buttons: "Voltar" (Go Back) / retry
- Clicking "Voltar" dismisses dialog, app remains usable

---

### Scenario 5: Not Found Screen

**Setup**: Delete a test account from backend but keep credentials.

**Steps**:
1. Launch app, auto-login sends valid key but account no longer exists
2. Backend returns 404

**Expected**:
- Full-screen overlay with danger-colored styling
- Title shows "Conta não encontrada" / "Account not found"
- Button: "Sair da conta" (Logout)
- Clicking "Sair da conta" clears credentials and shows Discord login screen

---

### Scenario 6: Generic Error Fallback

**Setup**: Trigger an unrecognized error from backend (e.g., 500 or unexpected message).

**Steps**:
1. Force an unexpected error response during auth

**Expected**:
- Full-screen overlay with neutral styling
- Title shows "Erro de autenticação" / "Authentication error"
- Body shows the raw error message
- Two buttons: "Tentar novamente" (Retry) and "Sair da conta" (Logout)

---

### Scenario 7: Translation Completeness

**Steps**:
1. Change app language to each supported locale (pt, en, es, fr)
2. Trigger each error screen category

**Expected**:
- All titles, body text, button labels, and help text appear in the correct language
- No missing translation keys (no raw key strings displayed)
- Placeholder substitution works (e.g., `{current}`, `{required}`, `{reason}`)

---

### Scenario 8: Logout from Error Screen

**Steps**:
1. Trigger any error screen
2. Click "Sair da conta" (Logout)

**Expected**:
- `felb_credentials.bin` is deleted
- In-memory token is cleared
- WebSocket is closed
- App shows Discord login screen (discordLoginOverlay in default state)
- User can log in with a different Discord account

## Automated Checks

```bash
# Python syntax/import check for modified controller
python -c "import py_compile; py_compile.compile('qt_controllers.py', doraise=True)"

# Verify translation keys exist in all catalogs
python -c "
import json, sys
required_keys = [
    'error.auth.blocked.title', 'error.auth.blocked.body',
    'error.auth.denied.title', 'error.auth.denied.body',
    'error.auth.reauth.title', 'error.auth.reauth.body',
    'error.auth.permission.title', 'error.auth.permission.body',
    'error.auth.not_found.title', 'error.auth.not_found.body',
    'error.auth.unknown.title', 'error.auth.unknown.body',
    'error.auth.btn.logout', 'error.auth.btn.retry',
    'error.auth.btn.signin_discord', 'error.auth.btn.go_back',
    'error.auth.btn.close_app',
]
for lang in ['pt', 'en', 'es', 'fr']:
    with open(f'translations/{lang}/translation.json', encoding='utf-8') as f:
        data = json.load(f)
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f'{lang}: MISSING {missing}')
        sys.exit(1)
    print(f'{lang}: OK ({len(required_keys)} keys found)')
print('All translation checks passed')
"
```
