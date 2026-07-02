# Implementation Plan: Auth Error Screens

**Branch**: `001-auth-error-screens` | **Date**: 2026-07-02 | **Spec**: [spec.md](file:///c:/Users/ryanl/OneDrive/Desktop/aplicativo/specs/001-auth-error-screens/spec.md)

**Input**: Feature specification from `specs/001-auth-error-screens/spec.md`

## Summary

The app currently shows all auth errors as a binary state (generic error or access denied) within the login overlay in Main.qml. This plan adds structured error classification in Python and a dedicated QML error overlay component that displays 5 category-specific screens (Blocked, Access Denied, Reauthentication, Permission, Not Found) plus a generic fallback — each with appropriate recovery actions (logout, retry, sign in with Discord, go back, close app). Additionally, hardcoded Portuguese admin panel error strings are migrated to the translation system.

## Technical Context

**Language/Version**: Python 3.x

**Primary Dependencies**: PySide6, Qt Quick/QML

**Storage**: Credential storage via `secure_store.py` (DPAPI), settings via `settings_store.py`. No new persistent data.

**Testing**: Manual desktop/QML validation for all 5 error screen categories + generic fallback. Python syntax/import checks for `qt_controllers.py`.

**Target Platform**: Windows desktop

**Project Type**: desktop-app

**Performance Goals**: Error classification adds negligible overhead (string matching on error payload). No impact on startup or auth latency.

**Constraints**: Must preserve existing login overlay behavior for non-error states. Must preserve tray/minimize/close behavior. Must support pt/en/es/fr translations.

**Scale/Scope**: Local single-user desktop app. Error screens are full-screen overlays during auth flow only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Desktop experience**: ✅ Plan modifies `qt_controllers.py` (controller), adds `qml/components/AuthErrorOverlay.qml` (QML component), and updates `Main.qml` (shell). All changes fit the PySide6/QML desktop shell. Tray/minimize/close flows preserved — error overlay is a child of the main window, not a separate window.
- **Local data safety**: ✅ No new file writes. Credential clearing uses existing `secure_clear_credentials()` in `secure_store.py`. No admin privileges needed.
- **Integration reliability**: ✅ Error screens are the graceful degradation mechanism itself — they handle auth failures from backend API. Network-offline errors use existing handling and are explicitly out of scope.
- **Verification**: ✅ Verification plan includes Python syntax/import checks for qt_controllers.py, manual QML validation for each error category screen, and translation catalog completeness check.
- **Internationalization and release discipline**: ✅ All new user-facing strings added via translation system in pt/en/es/fr. No new Python dependencies. Admin panel hardcoded strings migrated to i18n.

## Project Structure

### Documentation (this feature)

```text
specs/001-auth-error-screens/
|-- spec.md              # Feature specification
|-- plan.md              # This file
|-- research.md          # Phase 0 research decisions
|-- data-model.md        # Error classification data model
|-- quickstart.md        # Validation guide
|-- contracts/           # UI contracts
`-- tasks.md             # Implementation tasks (speckit-tasks)
```

### Source Code (repository root)

```text
qt_controllers.py        # Add error classification to ChatController._apply_result()
                         # Add new properties: authErrorCategory, authErrorData
                         # Migrate admin panel hardcoded strings to i18n
qml/
  Main.qml               # Wire AuthErrorOverlay into discordLoginOverlay
  components/
    AuthErrorOverlay.qml  # [NEW] Dedicated error screen component
translations/
  pt/translation.json    # Add error.auth.* keys
  en/translation.json    # Add error.auth.* keys
  es/translation.json    # Add error.auth.* keys
  fr/translation.json    # Add error.auth.* keys
```

**Structure Decision**: Changes are minimal and surgical — one new QML component, modifications to the existing controller and overlay, and translation additions. No new Python modules, frameworks, or file structures needed. This matches the existing GG Coalition architecture where controllers expose properties to QML.

## Complexity Tracking

No constitution violations. All changes use existing patterns:
- Python properties exposed to QML (existing pattern in ChatController)
- QML component with state-driven content (existing pattern in discordLoginOverlay)
- Translation keys with placeholders (existing pattern with `{reason}`, `{uri}`)
- Credential clearing via existing `secure_clear_credentials()` API
