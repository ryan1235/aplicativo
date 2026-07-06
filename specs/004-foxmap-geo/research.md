# Research: foxhole-geo-engine

## Decisions

**Decision**: Use Python's standard `math` module instead of `numpy`.
**Rationale**: The calculations are primarily done on single points or pairs of points for a single calculation at a time. The overhead of importing `numpy` and passing data back and forth isn't justified without heavy batch processing. `float64` precision is native to Python's float type on most platforms, satisfying the precision requirement.
**Alternatives considered**: Using `numpy` for vectorized operations (rejected because it adds a large dependency for simple point math).

**Decision**: Use Python `dataclasses` for data structures.
**Rationale**: The spec requires `foxmap.geo` to be purely functional and reusable without UI overhead. Dataclasses provide a clean, typed, and low-overhead way to pass around Coordinates and Overlay points.
**Alternatives considered**: Using plain dictionaries or tuples (rejected because they lack type safety and named attributes).
