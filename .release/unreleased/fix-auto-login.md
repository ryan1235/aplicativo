---
type: fix
area: auth
version: v0.0.0
user_visible: false
risk: low
requires_manual_test: true
---

# Summary

Fixed auto-login failing after the introduction of OAuth.

# User impact

Returning users who previously authorized the app via Discord will now be automatically logged in again without needing to click the connect button or interact with the OAuth popup.

# Technical notes

When the new OAuth flow was added to `_connect_with_discord`, the legacy flow that authenticated returning users via their saved Discord ID was accidentally bypassed. 
- Restored `_auth_with_discord(self._discord_auth_payload(saved_discord_id))` execution in the background worker when `allow_oauth=False` and a saved ID is present.
- Updated `autoConnectWithSavedDiscord` and `_maybe_auto_connect` to properly set `self._discord_login_required = False` during auto-connect, allowing the UI to progress.
- `connectWithDiscord` (manual login) continues to use the new `_auth_with_discord_oauth()` path exclusively.

# Changed files

- `qt_controllers.py`

# Validation performed

- Re-examined `ensureStarted` and QML triggers to ensure auto-login executes on app launch (specifically via `Main.qml`).
- Verified the backend POST fallback logic for `discordId` auth remains functional.
- Used review agent to ensure no security gaps.

# Release note draft

Corrigido falha no login automático do Discord para usuários já autenticados.
