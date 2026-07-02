# Data Model: Custom Notifications

## CustomNotification Entity

This entity represents a single custom timer created by the user.

- **ID** (String/UUID): Unique identifier for the notification.
- **ImageReference** (String): Path or key to the selected image.
- **DurationSeconds** (Integer): Total duration of the timer in seconds.
- **IsActive** (Boolean): Whether the timer is currently running.
- **PlaySound** (Boolean): Whether to play an audio alert when it finishes.
- **TimeRemainingSeconds** (Integer): Current remaining time. (Can be calculated dynamically or stored in memory).
