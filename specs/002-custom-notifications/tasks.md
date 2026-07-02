# Tasks: Custom Notifications

**Input**: Design documents from `/specs/002-custom-notifications/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests/Verification**: Include verification tasks required by the constitution. Add concrete Python checks and manual desktop/QML validation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm scope, affected files, and verification commands

- [ ] T001 Identify affected Python modules, QML files, translations, settings paths from `plan.md`
- [ ] T002 Confirm writable data paths and migration needs for this feature in `settings_store.py`
- [ ] T003 [P] Confirm supported translation catalogs that need updates in `translations/`
- [ ] T004 [P] Define manual checks for affected flows using `quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core behavior that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Establish CustomNotification schema and default settings in `settings_store.py`
- [ ] T006 [P] Add CustomNotification Python controller and QML bindings in `qt_controllers.py`
- [ ] T007 Add an image provider or asset model in `qt_controllers.py` to expose `img/` to QML

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create Custom Timer Notification (Priority: P1) MVP

**Goal**: Create custom notification timer with image and duration.

**Independent Test**: The user opens the app, goes to Notifications tab, clicks Create Custom Notification, selects an image from database, sets duration, toggles Active, and saves. Timer appears and counts down.

### Verification for User Story 1

- [ ] T008 [P] [US1] Add Python syntax/import check coverage for `qt_controllers.py`
- [ ] T009 [P] [US1] Document manual validation step in `quickstart.md` for US1

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement custom timer countdown logic and start/stop actions in `qt_controllers.py`
- [ ] T011 [P] [US1] Update `qml/pages/NotificationsPage.qml` to show a list of custom notifications and a Create button
- [ ] T012 [P] [US1] Create a form component in `qml/components/CustomNotificationForm.qml` for new custom notification inputs (duration, active toggle)
- [ ] T013 [P] [US1] Create an image selection card component with search input in `qml/components/ImageSelectionCard.qml` to pick images
- [ ] T014 [US1] Persist new custom notification data via `settings_store.py` upon saving
- [ ] T015 [P] [US1] Add translation strings (Create Custom Notification, Select Image, Search Images, Duration, Minutes, Hours, Active, Save, Cancel, No images found) in `translations/pt/translation.json`
- [ ] T016 [P] [US1] Add translation strings in `translations/en/translation.json`
- [ ] T017 [P] [US1] Add translation strings in `translations/es/translation.json`
- [ ] T018 [P] [US1] Add translation strings in `translations/fr/translation.json`
- [ ] T019 [US1] Run and record the independent validation for User Story 1

**Checkpoint**: User Story 1 is fully functional and independently verified

---

## Phase 4: User Story 2 - Toggle Sound for Custom Notification (Priority: P2)

**Goal**: Enable or disable sound for custom notifications.

**Independent Test**: User edits/creates a custom notification and toggles the Sound option on. When the timer reaches zero, the app plays an alert sound.

### Verification for User Story 2

- [ ] T020 [P] [US2] Add manual check to verify sound playing on timer end
- [ ] T021 [P] [US2] Check syntax in `qt_controllers.py`

### Implementation for User Story 2

- [ ] T022 [P] [US2] Add PlaySound property and audio alert trigger logic in `qt_controllers.py`
- [ ] T023 [P] [US2] Update `qml/components/CustomNotificationForm.qml` to include the "Play Sound" toggle
- [ ] T024 [P] [US2] Add translation strings (Play Sound) in all `translations/` catalogs
- [ ] T025 [US2] Run and record the independent validation for User Story 2

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T026 [P] Documentation updates in `README.md` if necessary
- [ ] T027 [P] Translation consistency check across pt/en/es/fr catalogs
- [ ] T028 Code cleanup and refactoring within affected files
- [ ] T029 Run Python syntax/import checks for all touched Python files
- [ ] T030 Run `quickstart.md` validation to ensure end-to-end functionality

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Can start after Foundational (Phase 2). May integrate with US1 UI changes.

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel
- Foundational tasks marked [P] can run in parallel
- Translation updates for different catalogs can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate User Story 1 independently in the desktop app
