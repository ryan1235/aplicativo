---
type: feature
area: auth
version: v0.0.0
user_visible: false
risk: medium
requires_manual_test: true
---

# Summary

Added GG activity logging for authenticated app actions through `POST /gg-logs`.

# User impact

User actions after secure login can now be recorded for dashboards and audits without changing the visible workflow.

# Technical notes

- Added a central `ChatController.logActivity(...)` helper that sends JSON to `/gg-logs` with the current chat token as `Authorization: Bearer ...`.
- Defined app activity categories and subcategories for auth, chat, autoclicker, stockpile, production, macros, notifications, settings, and navigation.
- Wired controllers to the central logger after `ChatController` is created, so unauthenticated startup actions are skipped safely.
- Instrumented high-level user actions while avoiding sensitive payloads such as message bodies and tokens.

# Changed files

- `qt_controllers.py`

# Validation performed

- `py -m py_compile qt_controllers.py debug_logging.py secure_store.py`
- `git diff --check`
- Searched active code for legacy auth routes and confirmed `/gg-logs` is the activity log route.

# Release note draft

Adicionado registro interno de a??es do aplicativo para auditoria e dashboards via logs GG autenticados.
