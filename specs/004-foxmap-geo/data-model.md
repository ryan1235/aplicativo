# Data Model: foxhole-geo-engine

## Entities

### `Point2D` (Dataclass)
Represents a generic 2D point.
- `x`: float
- `y`: float

### `ArtillerySolution` (Dataclass)
Represents the result of an artillery calculation.
- `distance_meters`: float
- `distance_kilometers`: float
- `distance_hexes`: float
- `bearing`: float
- `dx`: float
- `dy`: float

### `WeaponRangeStatus` (Enum/String)
Represents the target state relative to a weapon.
- `IN_RANGE`
- `OUT_OF_RANGE_MIN`
- `OUT_OF_RANGE_MAX`

### `GeoEngine`
Core config state.
- `scale`: float
- `offset_x`: float
- `offset_y`: float
- `hex_size_meters`: float
- `tile_size`: float
- `max_zoom`: float

### `Weapon`
Base class for weapon configuration.
- `min_range`: float
- `max_range`: float
