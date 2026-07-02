# Research: Custom Notifications

## Unknowns Resolved
- **Image Database**: The feature mentions an image database. We will read existing image resources from `img/` or a local dataset managed by the app, and expose them to QML via a model in `qt_controllers.py`.
- **Audio Alerts**: The app already has a mechanism for audio alerts (e.g., QSoundEffect or existing Python sound playing), we will reuse it.

## Best Practices
- **Timer Management**: The countdowns should be handled in a centralized QTimer or a Python background task that updates the remaining time, so that multiple timers can run concurrently without blocking the main UI thread. QML `Timer` elements can also be used if the logic is pure UI, but Python is safer for persisting and triggering background events.
