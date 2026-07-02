<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Template principle 1 -> I. Windows Desktop Experience Is Primary
- Template principle 2 -> II. Local Data Safety and User Control
- Template principle 3 -> III. Game Integration Reliability
- Template principle 4 -> IV. Verification Before Packaging
- Template principle 5 -> V. Internationalized UI and Release Discipline
Added sections:
- Platform and Runtime Constraints
- Development Workflow
Removed sections:
- None
Templates requiring updates:
- updated: .specify/templates/plan-template.md
- updated: .specify/templates/spec-template.md
- updated: .specify/templates/tasks-template.md
- not applicable: .specify/templates/commands/*.md (directory not present)
Follow-up TODOs:
- None
-->
# GG Coalition Constitution

## Core Principles

### I. Windows Desktop Experience Is Primary
GG Coalition is a Windows desktop application built with Python, PySide6, and
Qt Quick/QML. Features MUST preserve the desktop shell, tray behavior, overlay
behavior, and the existing Python-to-QML controller boundary unless a plan
explicitly justifies a migration. UI work MUST fit the current QML structure and
MUST keep the app usable from startup through minimize, tray, and close flows.

Rationale: the product value is the local desktop companion experience for
Foxhole users; server-first or web-first designs would weaken core workflows.

### II. Local Data Safety and User Control
Writable app data MUST be stored through the established app paths and settings
stores, preferring the user-writable GG Coalition data directory over the
executable directory. Features MUST preserve existing settings where practical,
avoid requiring administrator privileges, and make external calls or update
actions visible to the user when they affect files, releases, or gameplay tools.

Rationale: the app is distributed as a Windows executable and must survive
locked install locations, upgrades, and local user configuration.

### III. Game Integration Reliability
Steam, Foxhole, stockpile, overlay, and auto-clicker integrations MUST degrade
gracefully when the game, Steam cache, local files, processes, APIs, or network
resources are unavailable. Startup MUST NOT block indefinitely on integration
detection. Integration failures MUST be observable through logs, UI state, or
safe fallback behavior without corrupting saved settings.

Rationale: the app depends on local game state and external services that are
not always present, reachable, or consistent.

### IV. Verification Before Packaging
Every change MUST define and run targeted verification before it is considered
complete. Python changes MUST at minimum pass syntax/import-oriented checks for
affected modules when feasible. QML or user-flow changes MUST include a manual
or automated validation note for the affected screen. Changes touching builds,
updaters, release assets, or executable packaging MUST run the relevant build or
document why it was intentionally skipped.

Rationale: packaging failures and UI regressions are expensive once distributed
through executable releases.

### V. Internationalized UI and Release Discipline
User-facing strings MUST be added through the translation system and kept in
sync for the supported catalogs: Portuguese, English, Spanish, and French.
Release-facing changes MUST update version, packaging, and README guidance when
behavior changes. New dependencies MUST be recorded in `requirements-python.txt`
and justified by the feature plan.

Rationale: the app already supports multiple languages and GitHub Releases; new
features must not silently narrow that support.

## Platform and Runtime Constraints

The canonical runtime is Python with PySide6 and Qt Quick/QML on Windows. The
entry point is `felb_app.py`; controllers and models live primarily in
`qt_controllers.py`; QML screens live under `qml/`; translations live under
`translations/`; settings and path behavior live in `settings_store.py` and
`app_paths.py`; update behavior lives in `app_update.py` and `updater.py`.

Features MUST prefer existing modules, settings stores, logging helpers, and QML
component patterns over new frameworks. Networked integrations MUST use bounded
timeouts and offline-safe fallbacks. Generated outputs under build, dist,
release, extracted data, caches, and local user data are not source of truth and
MUST NOT be required for ordinary development unless the feature specifically
targets packaging or generated artifacts.

## Development Workflow

Feature plans MUST identify affected Python modules, QML files, translation
catalogs, settings/data paths, and external integrations. Work MUST be sliced by
independently testable user journeys. Tasks MUST include verification steps that
match the risk of the change, including manual desktop-flow validation where no
automated harness exists.

Before implementation, plans MUST pass the Constitution Check in
`.specify/templates/plan-template.md`. During review, any violation of these
principles MUST be listed in the plan's Complexity Tracking section with the
simpler alternative considered and the reason it was rejected.

## Governance

This constitution supersedes conflicting project practices for Spec Kit-driven
work. Amendments MUST be made by editing this file, updating dependent templates
or guidance in the same change, and recording the impact in the Sync Impact
Report at the top of this document.

Versioning follows semantic versioning:

- MAJOR: remove or redefine a principle in a way that invalidates existing
  compliant plans.
- MINOR: add a principle, add a governance section, or materially expand
  mandatory guidance.
- PATCH: clarify wording, fix typos, or make non-semantic refinements.

Compliance review is required for every feature plan and before packaging or
release work. Approved exceptions MUST be documented in the plan with a concrete
reason, affected files, and compensating verification.

**Version**: 1.0.0 | **Ratified**: 2026-06-27 | **Last Amended**: 2026-06-27

