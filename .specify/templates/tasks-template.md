---
description: "Task list template for GG Coalition feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests/Verification**: Include verification tasks required by the constitution. Add automated tests when requested or when an existing harness fits; otherwise add concrete Python checks and manual desktop/QML validation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Python app logic**: repository root modules such as `felb_app.py`, `qt_controllers.py`, `settings_store.py`
- **QML UI**: `qml/`
- **Translations**: `translations/pt/`, `translations/en/`, `translations/es/`, `translations/fr/`
- **Assets**: `img/`, `audio/`, `Content/`
- **Generated/local data**: `extracted/`, `user_data/`, `%LOCALAPPDATA%/GG Coalition` (only touch when required by the feature)
- **Packaging/release**: `build_exe.py`, `build_exe.bat`, `app_update.py`, `updater.py`, `release/`, `dist/`

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with priorities P1, P2, P3...)
  - Constitution checks and verification needs from plan.md
  - Data/settings behavior from spec.md and data-model.md
  - Integration contracts for Steam, Foxhole, stockpile API, or updater flows

  Tasks MUST be organized by user story so each story can be implemented,
  tested, and demonstrated independently.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm scope, affected files, and verification commands

- [ ] T001 Identify affected Python modules, QML files, translations, settings paths, and integrations from plan.md
- [ ] T002 Confirm writable data paths and migration needs for this feature
- [ ] T003 [P] Confirm supported translation catalogs that need updates
- [ ] T004 [P] Define verification commands/manual checks for affected flows

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core behavior that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T005 Establish settings/defaults in `settings_store.py` or related controller
- [ ] T006 [P] Add bounded timeout/error handling for any touched API or integration path
- [ ] T007 [P] Add or update shared QML component/controller bindings needed by all stories
- [ ] T008 Add logging or user-visible fallback state for recoverable integration failures
- [ ] T009 Update data model or generated-file handling without requiring administrator-only paths

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own in the desktop app]

### Verification for User Story 1

> **NOTE**: Add automated tests first when the feature spec requests them or an existing harness covers the risk. Otherwise define the manual desktop/QML check before implementation.

- [ ] T010 [P] [US1] Add automated test or documented manual check for [journey/failure state]
- [ ] T011 [P] [US1] Add Python syntax/import check coverage for affected modules

### Implementation for User Story 1

- [ ] T012 [P] [US1] Update controller/model behavior in [exact Python file]
- [ ] T013 [P] [US1] Update QML screen/component in [exact QML file]
- [ ] T014 [US1] Persist settings or generated data through approved app paths
- [ ] T015 [US1] Add safe fallback for missing Steam/Foxhole/API/local file state
- [ ] T016 [US1] Update user-facing strings in all supported translation catalogs
- [ ] T017 [US1] Run and record the independent validation for User Story 1

**Checkpoint**: User Story 1 is fully functional and independently verified

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Verification for User Story 2

- [ ] T018 [P] [US2] Add automated test or documented manual check for [journey/failure state]
- [ ] T019 [P] [US2] Add Python syntax/import check coverage for affected modules

### Implementation for User Story 2

- [ ] T020 [P] [US2] Update controller/model behavior in [exact Python file]
- [ ] T021 [P] [US2] Update QML screen/component in [exact QML file]
- [ ] T022 [US2] Integrate with User Story 1 components only where necessary
- [ ] T023 [US2] Update translations and fallback/error states
- [ ] T024 [US2] Run and record the independent validation for User Story 2

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Verification for User Story 3

- [ ] T025 [P] [US3] Add automated test or documented manual check for [journey/failure state]
- [ ] T026 [P] [US3] Add Python syntax/import check coverage for affected modules

### Implementation for User Story 3

- [ ] T027 [P] [US3] Update controller/model behavior in [exact Python file]
- [ ] T028 [P] [US3] Update QML screen/component in [exact QML file]
- [ ] T029 [US3] Update translations and fallback/error states
- [ ] T030 [US3] Run and record the independent validation for User Story 3

**Checkpoint**: All selected user stories are independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in `README.md` or feature docs
- [ ] TXXX [P] Translation consistency check across pt/en/es/fr catalogs
- [ ] TXXX Code cleanup and refactoring within affected files
- [ ] TXXX Performance/responsiveness validation for startup or integration polling
- [ ] TXXX Security/privacy review for local files, API calls, and update behavior
- [ ] TXXX Run Python syntax/import checks for affected modules
- [ ] TXXX Run packaging/build validation if updater, build script, dependencies, or release assets changed
- [ ] TXXX Run quickstart.md validation when a feature quickstart exists

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if they touch different files
  - Or sequentially in priority order (P1 -> P2 -> P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - may integrate with US1 but must remain independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - may integrate with US1/US2 but must remain independently testable

### Within Each User Story

- Verification approach before implementation
- Shared settings/data contracts before UI binding
- Controller/model behavior before QML consumption
- Core implementation before integration fallback polish
- Translations before story completion
- Story validation before moving to the next priority

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel
- Foundational tasks marked [P] can run in parallel when they touch different files
- User stories can run in parallel after Foundational if they do not conflict on the same Python/QML files
- Translation updates for different catalogs can run in parallel
- Manual checks for independent stories can run separately after each story is complete

---

## Parallel Example: User Story 1

```text
Task: "Update QML screen/component in qml/pages/[page].qml"
Task: "Update translations/en/translation.json for new labels"
Task: "Update translations/es/translation.json for new labels"
Task: "Update translations/fr/translation.json for new labels"
Task: "Update translations/pt/translation.json for new labels"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks user stories)
3. Complete Phase 3: User Story 1
4. Stop and validate User Story 1 independently in the desktop app
5. Package/demo only after constitution verification tasks pass or are documented

### Incremental Delivery

1. Complete Setup + Foundational -> foundation ready
2. Add User Story 1 -> validate independently -> demo
3. Add User Story 2 -> validate independently -> demo
4. Add User Story 3 -> validate independently -> demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories integrate only after independent validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to a specific user story for traceability
- Each user story must be independently completable and testable
- Use exact file paths in every implementation and verification task
- Record any skipped build, packaging, or manual validation with a reason
- Avoid vague tasks, same-file conflicts, and cross-story dependencies that break independence
