# GG Coalition v1.6.4

## Highlights
- Improved stockpile overlay flow to be clearer and less intrusive.
- Added full translation coverage for newly added UI texts across PT / EN / ES / FR.
- Updated Auto Clicker module with expanded modes, hotkey configuration, and better overlay status details.
- Improved startup and startup-shortcut behavior on Windows.

## Stockpile / API
- Added detailed stockpile flow diagnostics and logging for API requests/responses.
- Prevented temporary UI clearing during API refreshes by preserving previous snapshot data.
- Added support for `WarehouseLastUpdate` in API-driven views and item details.
- Improved notification behavior:
  - Overlay now focuses on real updates.
  - Reduced noisy notifications on passive map open / non-update paths.
  - Sound alerts remain tied to meaningful update events.

## Auto Clicker
- Restored original auto-clicker behavior and integrated new advanced modes.
- Added extra actions (move-click, fixed double-click, pilot sequence, slot triggers).
- Added configurable hotkeys with key-capture UX in settings.
- Added clearer in-app and overlay descriptions of active actions.
- Added scroll support to keep the Auto Clicker page fluid with larger content.

## Identify Item
- Improved integration of Identify Item into app layout and category navigation.
- Added support for image input via clipboard paste (Ctrl+V).
- Added additional debug outputs to help track detection and monitoring flow.

## Stability / UX
- Improved language switch and dynamic text refresh behavior.
- Fixed multiple edge-case regressions reported during live testing.
- General polish for flow consistency between categories and overlay states.
