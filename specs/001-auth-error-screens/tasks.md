# Tasks: Auth Error Screens

**Input**: Design documents from `specs/001-auth-error-screens/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests/Verification**: Include verification tasks required by the constitution. Add automated tests when requested or when an existing harness fits; otherwise add concrete Python checks and manual desktop/QML validation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm scope, affected files, and verification commands

- [ ] T001 Confirm affected Python modules (`qt_controllers.py`), QML files (`qml/Main.qml`, `qml/components/AuthErrorOverlay.qml`), and translation catalogs (`translations/*/translation.json`) from `plan.md`
- [ ] T002 Confirm that no new writable data paths or migrations are needed for this feature
- [ ] T003 [P] Confirm pt, en, es, fr translation catalogs are ready to receive new keys
- [ ] T004 [P] Define verification commands in `quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core behavior that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Update `qt_controllers.py` to add the new `authErrorCategory`, `authErrorMessage`, `authErrorBlockedReason`, `authErrorBlockedAt`, `authErrorCurrentLevel`, and `authErrorRequiredLevel` properties to the `ChatController` class.
- [ ] T006 Update `qt_controllers.py` to add `_classify_auth_error(payload)` helper method for error classification rules defined in `data-model.md`.
- [ ] T007 Create new `AuthErrorOverlay.qml` component in `qml/components/` with empty placeholders based on `ui-contract.md`.
- [ ] T008 Update `Main.qml` to integrate `AuthErrorOverlay.qml` inside `discordLoginOverlay`.

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Blocked Account Screen (Priority: P1)

**Goal**: A user whose GG account has been blocked sees a dedicated full-screen error state explaining that their account is blocked, showing the reason and the date/time of the block.

**Independent Test**: Scenario 1 in `quickstart.md`

### Verification for User Story 1

- [ ] T009 [P] [US1] Review manual check instructions for Scenario 1 in `quickstart.md`
- [ ] T010 [P] [US1] Ensure Python syntax/import check covers `qt_controllers.py`

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implement BLOCKED classification rule in `_classify_auth_error()` in `qt_controllers.py`
- [ ] T012 [P] [US1] Update `AuthErrorOverlay.qml` to handle the `BLOCKED` state, binding properties `blockedReason` and `blockedAt`, and adding `logoutClicked()` and `closeAppClicked()` connections.
- [ ] T013 [P] [US1] Add `error.auth.blocked.*` and related common button keys to `translations/en/translation.json`
- [ ] T014 [P] [US1] Add `error.auth.blocked.*` and related common button keys to `translations/pt/translation.json`
- [ ] T015 [P] [US1] Add `error.auth.blocked.*` and related common button keys to `translations/es/translation.json`
- [ ] T016 [P] [US1] Add `error.auth.blocked.*` and related common button keys to `translations/fr/translation.json`
- [ ] T017 [US1] Connect `closeAppClicked()` signal in `Main.qml` to exit the application.
- [ ] T018 [US1] Connect `logoutClicked()` signal in `Main.qml` to `chatController.logout()`.
- [ ] T019 [US1] Run and record the independent validation for User Story 1

**Checkpoint**: User Story 1 is fully functional and independently verified

---

## Phase 4: User Story 2 - Access Denied Screen (Priority: P1)

**Goal**: A user whose access level is insufficient sees a dedicated Access Denied Screen that explains their current access level versus the required level.

**Independent Test**: Scenario 2 in `quickstart.md`

### Verification for User Story 2

- [ ] T020 [P] [US2] Review manual check instructions for Scenario 2 in `quickstart.md`
- [ ] T021 [P] [US2] Ensure Python syntax/import check covers `qt_controllers.py`

### Implementation for User Story 2

- [ ] T022 [P] [US2] Implement ACCESS_DENIED classification rule in `_classify_auth_error()` in `qt_controllers.py`
- [ ] T023 [P] [US2] Update `AuthErrorOverlay.qml` to handle the `ACCESS_DENIED` state, binding properties `currentLevel` and `requiredLevel`.
- [ ] T024 [P] [US2] Add `error.auth.denied.*` translation keys to `translations/en/translation.json`
- [ ] T025 [P] [US2] Add `error.auth.denied.*` translation keys to `translations/pt/translation.json`
- [ ] T026 [P] [US2] Add `error.auth.denied.*` translation keys to `translations/es/translation.json`
- [ ] T027 [P] [US2] Add `error.auth.denied.*` translation keys to `translations/fr/translation.json`
- [ ] T028 [US2] Connect `retryClicked()` signal in `Main.qml` to `chatController.connectWithDiscord()`.
- [ ] T029 [US2] Run and record the independent validation for User Story 2

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - Reauthentication Screen (Priority: P1)

**Goal**: A user whose token is invalid, session is expired, or auto-login key is invalid sees a Reauthentication Screen.

**Independent Test**: Scenario 3 in `quickstart.md`

### Verification for User Story 3

- [ ] T030 [P] [US3] Review manual check instructions for Scenario 3 in `quickstart.md`
- [ ] T031 [P] [US3] Ensure Python syntax/import check covers `qt_controllers.py`

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement REAUTH classification rule in `_classify_auth_error()` in `qt_controllers.py`
- [ ] T033 [P] [US3] Ensure `qt_controllers.py` auto-clears credentials for REAUTH failures.
- [ ] T034 [P] [US3] Update `AuthErrorOverlay.qml` to handle the `REAUTH` state.
- [ ] T035 [P] [US3] Add `error.auth.reauth.*` translation keys to `translations/en/translation.json`
- [ ] T036 [P] [US3] Add `error.auth.reauth.*` translation keys to `translations/pt/translation.json`
- [ ] T037 [P] [US3] Add `error.auth.reauth.*` translation keys to `translations/es/translation.json`
- [ ] T038 [P] [US3] Add `error.auth.reauth.*` translation keys to `translations/fr/translation.json`
- [ ] T039 [US3] Connect `signinClicked()` signal in `Main.qml` to `chatController.connectWithDiscord()`.
- [ ] T040 [US3] Run and record the independent validation for User Story 3

**Checkpoint**: User Stories 1, 2, and 3 both work independently

---

## Phase 6: User Story 4 - Permission Screen (Priority: P2)

**Goal**: A user who tries to access an admin or restricted feature without sufficient permissions sees a Permission Screen explaining the required role.

**Independent Test**: Scenario 4 in `quickstart.md`

### Verification for User Story 4

- [ ] T041 [P] [US4] Review manual check instructions for Scenario 4 in `quickstart.md`
- [ ] T042 [P] [US4] Ensure Python syntax/import check covers `qt_controllers.py`

### Implementation for User Story 4

- [ ] T043 [P] [US4] Implement PERMISSION classification rule in `_classify_auth_error()` in `qt_controllers.py`
- [ ] T044 [P] [US4] Migrate hardcoded Portuguese admin panel error strings to use translation system via `self._t` in `qt_controllers.py` (around L1531-1669).
- [ ] T045 [P] [US4] Add `error.auth.permission.*` translation keys to `translations/en/translation.json`
- [ ] T046 [P] [US4] Add `error.auth.permission.*` translation keys to `translations/pt/translation.json`
- [ ] T047 [P] [US4] Add `error.auth.permission.*` translation keys to `translations/es/translation.json`
- [ ] T048 [P] [US4] Add `error.auth.permission.*` translation keys to `translations/fr/translation.json`
- [ ] T049 [US4] Update `AuthErrorOverlay.qml` and/or `startupDialog` in `Main.qml` to handle the new localized permission error messages.
- [ ] T050 [US4] Connect `goBackClicked()` signal in `Main.qml` (if applicable) to dismiss the dialog.
- [ ] T051 [US4] Run and record the independent validation for User Story 4

**Checkpoint**: User Stories 1, 2, 3, and 4 both work independently

---

## Phase 7: User Story 5 - Not Found Screen (Priority: P2)

**Goal**: A user whose profile, chat account, or requested resource cannot be found sees a Not Found Screen.

**Independent Test**: Scenario 5 in `quickstart.md`

### Verification for User Story 5

- [ ] T052 [P] [US5] Review manual check instructions for Scenario 5 in `quickstart.md`
- [ ] T053 [P] [US5] Ensure Python syntax/import check covers `qt_controllers.py`

### Implementation for User Story 5

- [ ] T054 [P] [US5] Implement NOT_FOUND classification rule in `_classify_auth_error()` in `qt_controllers.py`
- [ ] T055 [P] [US5] Ensure `qt_controllers.py` auto-clears credentials for NOT_FOUND failures.
- [ ] T056 [P] [US5] Update `AuthErrorOverlay.qml` to handle the `NOT_FOUND` state.
- [ ] T057 [P] [US5] Add `error.auth.not_found.*` translation keys to `translations/en/translation.json`
- [ ] T058 [P] [US5] Add `error.auth.not_found.*` translation keys to `translations/pt/translation.json`
- [ ] T059 [P] [US5] Add `error.auth.not_found.*` translation keys to `translations/es/translation.json`
- [ ] T060 [P] [US5] Add `error.auth.not_found.*` translation keys to `translations/fr/translation.json`
- [ ] T061 [US5] Run and record the independent validation for User Story 5

**Checkpoint**: All selected user stories are independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T062 [P] Add `error.auth.unknown.*` generic fallback translation keys to `translations/en/translation.json`, `translations/pt/translation.json`, `translations/es/translation.json`, and `translations/fr/translation.json`.
- [ ] T063 Update `AuthErrorOverlay.qml` to handle `UNKNOWN` state fallback.
- [ ] T064 Test Scenario 6 (Generic Error Fallback) in `quickstart.md`.
- [ ] T065 [P] Translation consistency check across pt/en/es/fr catalogs (Scenario 7)
- [ ] T066 Verify Logout functionality from Error Screens (Scenario 8)
- [ ] T067 Run Python syntax/import checks for `qt_controllers.py` via `python -c "import py_compile; py_compile.compile('qt_controllers.py', doraise=True)"`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed sequentially or in parallel.
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### Parallel Opportunities

- Translation updates for different catalogs can run in parallel
- Manual checks for independent stories can run separately after each story is complete
