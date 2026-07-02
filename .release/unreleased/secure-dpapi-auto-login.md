---
type: security
area: auth
version: v0.0.0
user_visible: false
risk: low
requires_manual_test: true
---

# Summary

Migrated auto-login from insecure Discord ID fallback to a secure DPAPI session-based mechanism.

# User impact

Auto-login is now completely secure and relies on an OS-encrypted session key rather than sending the public Discord ID to a legacy endpoint.

# Technical notes

- Created `secure_store.py` leveraging Windows DPAPI (`ctypes.windll.crypt32.CryptProtectData`) to securely encrypt the `autoLoginKey` and `accessPassword` bound to the active Windows user.
- Updated the OAuth/auth result handling to capture and encrypt the keys returned by `/chat/auth/discord/oauth`.
- Re-routed the auto-login thread (`worker` inside `_connect_with_discord`) to attempt `POST /chat/auth/auto-login` with the decrypted keys instead of building a fallback payload.
- In case of 401/403 (invalid keys), the secure DPAPI blob is deleted locally, and the client gracefully reverts to the interactive OAuth prompt without falling back to the legacy endpoint.
- Redacted `autoLoginKey`, `accessPassword`, and related aliases from login/debug logging.

# Changed files

- `secure_store.py`
- `qt_controllers.py`
- `debug_logging.py`

# Validation performed

- Ensured DPAPI structures align with Windows x64 architecture.
- Checked that OAuth fallbacks cleanly clear the encrypted files and don't loop endlessly.
- The backend changes (adding `/chat/auth/auto-login`) were confirmed successful.
