# GG Coalition Project Context

## Product

GG Coalition is a Windows desktop application for Foxhole coalition operations. It is built around a Python backend with a PySide6/QML interface and tooling for coordination, logistics, automation, chat, and release delivery.

## Core Capabilities

- Discord OAuth2 login and identity/profile integration.
- Realtime chat and coalition communication flows.
- Stockpile and logistics workflows for Foxhole resources.
- Wiki Foxhole reference and structured game information.
- Auto clicker, auto pilot, macro, and time task utilities.
- Updater, installer, and packaged Windows builds.
- Nuitka-based executable build process.
- Multilingual UI in Portuguese, English, Spanish, and French.
- User personalization, color system, themes, and colorblind mode.

## Technology

- Language: Python.
- Desktop shell: PySide6 with QML.
- Target OS: Windows.
- Build and release: Nuitka, local installer/updater scripts, release artifacts.
- Data and settings: local JSON/configuration files and local database artifacts.
- Localization: translation files and runtime i18n helpers.

## Important Paths

- `felb_app.py`: application entry point and app bootstrap.
- `qt_controllers.py`: large Qt/PySide controller surface.
- `qml/`: QML UI files.
- `translations/`: translation resources.
- `stockpiler.py`: stockpile and logistics domain logic.
- `i18n.py`: runtime localization helpers.
- `settings_store.py`: persisted local settings.
- `app_update.py`, `updater.py`, `web_installer.py`: update and installer surfaces.
- `build_exe.py`, `GG Coalition.spec`: build and packaging entry points.
- `.agents/`: project agent documentation and workflow guidance.
- `.codex/agents/`: Codex agent configuration files.

## Current Task Guardrails

For this agent-structure setup, only documentation and agent configuration files may be created or changed.

Do not modify:

- Existing files under `.agents/skills/`.
- Application source code.
- `qml/`.
- `translations/`.
- `qt_controllers.py`.
- Database files or migration/data artifacts.

## Persistent Engineering Guardrails

- Prefer small, scoped changes that preserve the existing desktop architecture.
- Treat `qt_controllers.py` as high-risk because it is broad and central.
- Treat QML and Python controller contracts as coupled; validate signal/property names when changing either side.
- Keep Windows packaging behavior in mind when adding imports, assets, or runtime file paths.
- Do not introduce network-dependent behavior into startup paths unless explicitly required.
- Preserve translation coverage when user-facing text changes.
- Preserve accessibility choices, especially colorblind mode and the existing color system.
- Avoid changing automation behavior without a clear QA path because auto clicker, auto pilot, and time task features affect user input.

## Validation Expectations

Choose validation based on the change:

- Documentation/config-only: inspect created files and verify no app source files changed.
- Python logic: run focused Python checks or compile checks where practical.
- QML/UI: launch the desktop app when feasible and verify bindings visually.
- i18n: verify all supported locales have equivalent keys and no fallback regressions.
- Build/updater: verify build scripts, updater paths, version metadata, and Windows artifact names.
- Release notes: verify user-facing wording against actual changed files.
