# Feature Specification: foxmap.geo

**Feature Branch**: `[004-foxmap-geo]`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "criem em uma nova utilizade do mapa utilize obrigatroriamente o sistema de skills..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coordinate Conversion (Priority: P1)

As a map utility developer, I want to convert between different coordinate systems (World, Pixel, Tile, Meters, HEX, Screen) so that map elements can be accurately positioned.

**Why this priority**: Coordinate conversion is the foundation of all spatial math on the map.

**Independent Test**: Can be tested independently via unit tests confirming known conversion values.

**Acceptance Scenarios**:

1. **Given** a world coordinate, **When** converted to hex, **Then** the correct hex grid coordinate is returned.
2. **Given** a screen coordinate, **When** converted to world, **Then** the correct game world coordinate is returned.

---

### User Story 2 - Artillery Calculations (Priority: P1)

As an artillery calculator developer, I want to calculate distance, bearing, and angle between a cannon and a target, so that players can aim accurately.

**Why this priority**: Artillery calculator is a primary feature relying on this math.

**Independent Test**: Can be tested via unit tests using known in-game artillery examples.

**Acceptance Scenarios**:

1. **Given** two world coordinates, **When** calculating artillery parameters, **Then** correct distance, bearing, dx, and dy are returned.

---

### User Story 3 - Weapon Ranges (Priority: P2)

As a map overlay developer, I want to verify if a target is within weapon range and generate range rings (min/max), so that I can visualize weapon capabilities on the map.

**Why this priority**: Essential for tactical map features like weapon overlays.

**Independent Test**: Can be tested independently via unit tests validating point-in-circle and range polygon generation.

**Acceptance Scenarios**:

1. **Given** a weapon with min and max range, **When** checking a target distance, **Then** it correctly reports if the target is in range, out of range, or distance to limit.
2. **Given** a weapon, **When** requesting overlay rings, **Then** the correct mathematical points are returned (without drawing).

### Edge Cases

- What happens when zoom or scale values are extremely small (approaching 0) or negative?
- What happens when coordinates are far outside the standard map boundaries?
- What happens when calculating bearing for identical start and end points?
- What happens when precision errors accumulate in multiple conversion steps?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `GeoEngine` class that converts coordinates between World, Pixel, Tile, Meters, HEX, and Screen.
- **FR-002**: System MUST provide distance calculations returning World Units, Pixels, Tiles, Meters, and HEXes.
- **FR-003**: System MUST provide geometry functions including bearing, angle, midpoint, and interpolate.
- **FR-004**: System MUST expose configuration for SCALE, OFFSET_X, OFFSET_Y, HEX_SIZE_METERS, TILE_SIZE, and MAX_ZOOM.
- **FR-005**: System MUST provide an `ArtilleryCalculator` class that takes cannon position, target position, zoom, and scale, and returns Distance (meters, km, hexes), Azimuth/Bearing, Angle, dx, and dy.
- **FR-006**: System MUST provide a `WeaponRange` class to check `target_in_range()`, `target_out_of_range()`, `remaining_distance()`, and `distance_to_limit()`.
- **FR-007**: System MUST allow configuring specific weapons like `StormCannon` or `Rocket` with min and max ranges.
- **FR-008**: System MUST provide overlay geometry functions (circle, min_ring, max_ring, polygon, bounding_box) that return points without executing UI/drawing code.
- **FR-009**: System MUST use float64 precision internally and only round on final output.
- **FR-010**: System MUST NOT include any UI or drawing code.
- **FR-011**: System MUST be designed to allow future extensions (wind, ballistic drift, height, elevation, obstacles) without altering existing APIs.

### Integration & Offline Behavior

- **Independent Module**: The math library MUST be completely standalone and run offline without depending on the game client or network.

### Key Entities

- **GeoEngine**: The core coordinate system conversion and distance calculator.
- **ArtilleryCalculator**: Calculates firing solutions between two points.
- **WeaponRange**: Defines a weapon's capability and tests targets against it.
- **OverlayPoints**: Data structure containing mathematical points for rendering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All coordinate conversions (World -> Pixel -> Tile -> Meters -> HEX -> Screen) match expected manual calculation values within 0.001 precision.
- **SC-002**: The provided artillery example returns exact expected values: `{ "meters":1548.3, "kilometers":1.548, "hexes":0.774, "bearing":213.6, "dx":19.93, "dy":-34.78 }`
- **SC-003**: 100% of the mathematical functions are covered by unit tests (distance, bearing, world_to_pixel, pixel_to_world, range).
- **SC-004**: Code contains zero UI/rendering library dependencies (no PySide6/QML/Leaflet imports in `foxmap.geo`).
- **SC-005**: Code passes PEP8 linter without errors.
- **SC-006**: All public methods include type hints and docstrings with usage examples.

## Assumptions

- The game world uses a flat 2D projection for standard map calculations.
- Standard 1 HEX width is approximately 1000 meters for calculation purposes, and point-to-point is 2000 meters.
- World coordinates are defined as float values as found in `coordinates.json`.
- The developer will provide the necessary scale, offset, and tile size constants during initialization based on the specific map being viewed.
