---
type: fix
area: auth
version: v0.0.0
user_visible: true
risk: medium
requires_manual_test: true
---

# Summary

Fixed secure Discord auto-login after the OAuth migration.

# User impact

Returning users with a valid OAuth session key can be logged in automatically without falling back to legacy Discord, login, or Steam authentication endpoints.

# Technical notes

- Auto-connect now uses only `POST /chat/auth/auto-login` when a DPAPI-protected `autoLoginKey` exists.
- Manual Discord login continues to use only `POST /chat/auth/discord/oauth`.
- Removed a duplicated broken `connectWithDiscord` block that referenced undefined `result`, `user`, and `token` values.
- Successful auth responses persist `autoLoginKey`/`accessPassword` via DPAPI for future secure auto-login.
- Logout and reauthentication-required auto-login failures clear the local DPAPI credential blob.

# Changed files

- `qt_controllers.py`
- `debug_logging.py`

# Validation performed

- `py -m py_compile qt_controllers.py debug_logging.py secure_store.py`
- Searched active code for legacy `/chat/auth/discord`, `/chat/auth/login`, `/chat/auth/steam`, and `/chat/auth/local` usage outside historical dump/patch files.

# Release note draft

Corrigido o login seguro do Discord para usar OAuth e auto-login seguro sem retornar aos endpoints antigos.
