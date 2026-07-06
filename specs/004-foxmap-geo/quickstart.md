# Quickstart Validation Guide: foxhole-geo-engine

## Overview
This guide provides steps to validate the `foxmap.geo` math utility works as expected in isolation.

## Setup
No special setup is required as this is a pure Python standard-library module.

## Validation Scenarios

### 1. Run Unit Tests
Run the provided unit tests to validate all math conversions and distances.

**Command:**
```bash
pytest tests/test_geo.py -v
```

**Expected Outcome:**
All tests pass, confirming the accuracy of coordinate conversions, artillery logic, and weapon ranges.

### 2. Manual Python Verification
Open a Python REPL and test the ArtilleryCalculator.

**Commands:**
```python
from foxmap.geo.artillery import ArtilleryCalculator

# Cannon at 100.22, -80.55 and Target at 120.15, -115.33
calc = ArtilleryCalculator()
solution = calc.calculate((100.22, -80.55), (120.15, -115.33))
print(f"Distance: {solution.distance_meters}m, Bearing: {solution.bearing}°")
```

**Expected Outcome:**
The script outputs: `Distance: 1548.3m, Bearing: 213.6°` (rounded to 1 decimal).
