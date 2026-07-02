# Implementation Plan: Custom Notifications

**Branch**: `[002-custom-notifications]` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-custom-notifications/spec.md`

## Summary

Add a new section in the Notifications tab to allow users to create custom notifications (timers) with a specific image from the local database, configurable duration (minutes/hours), sound toggle, and active state.

## Technical Context

**Language/Version**: Python 3.x

**Primary Dependencies**: PySide6, Qt Quick/QML

**Storage**: Local settings/data through `settings_store.py` (`felb_settings.json`).

**Testing**: Targeted Python syntax/import checks, focused automated tests when present, and manual desktop/QML validation for affected screens.

**Target Platform**: Windows desktop

**Project Type**: desktop-app

**Performance Goals**: Responsive UI when searching images in the image card (under 500ms).

**Constraints**: Must preserve tray/minimize/close behavior, user-writable data paths, and supported translations.

**Scale/Scope**: Local single-user desktop companion.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Desktop experience**: The feature uses PySide6 and QML. Will update `qt_controllers.py` and QML files in `qml/` to add the custom notifications UI.
- **Local data safety**: Persists notifications in existing `settings_store.py`.
- **Integration reliability**: Safe fallbacks if image DB is empty.
- **Verification**: Will test manually using the desktop app.
- **Internationalization and release discipline**: Will add user-facing strings to translation catalogs.

## Project Structure

### Documentation (this feature)

```text
specs/002-custom-notifications/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- tasks.md
```

### Source Code (repository root)

```text
qt_controllers.py        # Add custom notification management logic
qml/pages/NotificationsPage.qml # UI for custom notifications list and creation
qml/components/          # Image selection card / modal component
translations/            # pt/en/es/fr translation catalogs updates
settings_store.py        # Persistence for custom notifications
```

**Structure Decision**: Custom notifications fit perfectly into the existing Notifications page and the general controller/model structure.
