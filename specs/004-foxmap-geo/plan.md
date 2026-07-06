# Implementation Plan: foxhole-geo-engine

**Branch**: `[004-foxmap-geo]` | **Date**: 2026-07-06 | **Spec**: [specs/004-foxmap-geo/spec.md](file:///c:/Users/ryanl/OneDrive/Desktop/aplicativo/specs/004-foxmap-geo/spec.md)

**Input**: Feature specification from `specs/004-foxmap-geo/spec.md`

## Summary

Create a new geospatial math utility module called `foxmap.geo` responsible for all spatial math in Foxhole. It will convert coordinates, calculate distances, compute artillery firing parameters, and generate weapon range overlay geometries. The module will be purely functional, independent of UI (PySide6/QML/Leaflet), and thoroughly unit-tested.

## Technical Context

**Language/Version**: Python 3.x

**Primary Dependencies**: Standard library `math`, `dataclasses`. No external UI libraries.

**Storage**: In-memory math calculations only.

**Testing**: Python `unittest` or `pytest` suite covering math functions.

**Target Platform**: Any (pure python module).

**Project Type**: Python utility module.

**Performance Goals**: Fast calculations using float64 math.

**Constraints**: MUST remain independent of UI/GUI. No QML or Leaflet dependencies in `foxmap.geo`.

**Scale/Scope**: Local utility module for all map spatial math.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Desktop experience**: N/A for this module, it is headless math.
- **Local data safety**: Math is purely in-memory.
- **Integration reliability**: Completely standalone and offline.
- **Verification**: Dedicated test file `test_geo.py`.
- **Internationalization and release discipline**: N/A, internal developer API.

## Project Structure

### Documentation (this feature)

```text
specs/004-foxmap-geo/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- tasks.md
```

### Source Code (repository root)

```text
foxmap/
|-- geo/
|   |-- __init__.py          # Exposes the API
|   |-- engine.py            # GeoEngine class for conversions
|   |-- artillery.py         # ArtilleryCalculator
|   |-- weapons.py           # WeaponRange and subclasses
|   `-- overlay.py           # Geometric points for overlays
tests/
`-- test_geo.py              # Unit tests for the module
```

**Structure Decision**: A new `foxmap` package or directory is introduced, keeping the geo-math isolated in `foxmap.geo` as requested by the user, and test files in `tests/`.
