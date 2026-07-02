---
type: security
area: auth
version: v0.0.0
user_visible: false
risk: low
requires_manual_test: true
---

# Summary

Removed raw JWT/apiToken exposure from QML console output in HomePage.qml.

# User impact

None — internal debug log only. No user-facing text changed.

# Technical notes

The `console.log` in `HomePage.qml` line 29 was printing `chatController.apiToken` (the full JWT) to the QML console every time the `chatController.changed` signal fired. Replaced with `tokenPresent: true/false` and `tokenLength: N` to preserve debug value without leaking the token.

# Changed files

- `qml/pages/HomePage.qml`

# Validation performed

- Grep scan for `apiToken`, `accessToken`, `refreshToken`, `autoLoginKey`, `accessPassword`, `console.log`, and `print(` across QML and Python files.
- Confirmed `debug_logging.py` already redacts tokens via `SENSITIVE_KEYS`.
- Confirmed `redact_login_debug()` in `qt_controllers.py` already redacts tokens in `debug_login_response()`.
- Confirmed `Main.qml`, other QML pages, and QML components have no additional token leaks.

# Release note draft

Corrigido vazamento de token JWT no console de debug QML.
