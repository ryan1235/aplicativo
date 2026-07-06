# Tasks: foxhole-geo-engine

**Input**: Design documents from `specs/004-foxmap-geo/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests/Verification**: Unit tests as requested by spec.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm scope, affected files, and set up the module structure.

- [X] T001 Identify affected Python modules and module structure from plan.md
- [X] T002 [P] Create the package structure `foxmap/geo/` and `tests/` directories.
- [X] T003 [P] Initialize `foxmap/__init__.py` and `foxmap/geo/__init__.py` to expose the API.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core behavior that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Define shared `Point2D` dataclass and basic math utilities in `foxmap/geo/utils.py`
- [X] T005 [P] Define `GeoEngine` configuration parameters in `foxmap/geo/engine.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Coordinate Conversion (Priority: P1) MVP

**Goal**: Convert between different coordinate systems (World, Pixel, Tile, Meters, HEX, Screen)

**Independent Test**: Can be tested independently via unit tests confirming known conversion values.

### Verification for User Story 1

- [X] T006 [P] [US1] Create unit tests in `tests/test_geo.py` for all coordinate conversions.

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement `world_to_pixel`, `pixel_to_world` in `foxmap/geo/engine.py`
- [X] T008 [P] [US1] Implement `world_to_tile`, `tile_to_world`, `pixel_to_tile`, `tile_to_pixel` in `foxmap/geo/engine.py`
- [X] T009 [P] [US1] Implement `world_to_screen`, `screen_to_world` in `foxmap/geo/engine.py`
- [X] T010 [P] [US1] Implement `world_to_hex`, `hex_to_world` in `foxmap/geo/engine.py`
- [X] T011 [US1] Implement distance methods (`distance_world`, `distance_pixels`, `distance_meters`, `distance_hex`) in `foxmap/geo/engine.py`
- [X] T012 [US1] Run unit tests and verify User Story 1 passes successfully.

**Checkpoint**: User Story 1 is fully functional and independently verified

---

## Phase 4: User Story 2 - Artillery Calculations (Priority: P1)

**Goal**: Calculate distance, bearing, and angle between a cannon and a target.

**Independent Test**: Unit tests with known in-game artillery examples.

### Verification for User Story 2

- [X] T013 [P] [US2] Create unit tests in `tests/test_geo.py` for ArtilleryCalculator with example parameters.

### Implementation for User Story 2

- [X] T014 [US2] Create `ArtillerySolution` dataclass in `foxmap/geo/artillery.py`
- [X] T015 [US2] Implement `ArtilleryCalculator` class in `foxmap/geo/artillery.py` returning Distance, Bearing, dx, dy.
- [X] T016 [US2] Run unit tests and verify User Story 2 passes successfully.

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - Weapon Ranges (Priority: P2)

**Goal**: Verify if a target is within weapon range and generate overlay rings points.

**Independent Test**: Unit tests validating target_in_range logic and overlay points generation.

### Verification for User Story 3

- [X] T017 [P] [US3] Create unit tests in `tests/test_geo.py` for WeaponRange and geometric overlays.

### Implementation for User Story 3

- [X] T018 [P] [US3] Create `WeaponRange` class and subclass `StormCannon`, `Rocket` in `foxmap/geo/weapons.py`
- [X] T019 [US3] Implement `target_in_range()`, `target_out_of_range()`, `remaining_distance()` in `foxmap/geo/weapons.py`
- [X] T020 [US3] Implement geometry functions for overlays (circle, min_ring, max_ring, polygon, bounding_box) in `foxmap/geo/overlay.py`
- [X] T021 [US3] Run unit tests and verify User Story 3 passes successfully.

**Checkpoint**: All selected user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T022 [P] Format code according to PEP8 using black or flake8 validation.
- [X] T023 [P] Ensure all public methods have type hints and complete docstrings.
- [X] T024 Run `pytest tests/test_geo.py` one final time to validate the entire suite.
