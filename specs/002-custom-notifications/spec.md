# Feature Specification: Custom Notifications

**Feature Branch**: `[002-custom-notifications]`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "na aba de notificação ter uma forma de criar notificações personalizada... aonde o usuario pode escolher uma imagem (abre um card de imagem com um input de busca das imagens que ja tem no banco de dados verifique para ver) pode escolher o time, minutos ou horas... aonde ele cria o time e pode ser ativo colocar o som etc.. etc.. etc.. "

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Custom Timer Notification (Priority: P1)

As a user, I want to create a custom notification timer with a specific image and duration, so that I can be reminded of custom events during gameplay.

**Why this priority**: Core functionality for custom notifications as requested by the user.

**Independent Test**: The user opens the app, goes to the Notifications tab, clicks "Create Custom Notification", selects an image from the database, sets a duration in minutes/hours, toggles "Active", and saves. The timer appears and counts down.

**Acceptance Scenarios**:

1. **Given** the user is on the Notifications tab, **When** they click to create a custom notification, **Then** a creation form/modal opens.
2. **Given** the custom notification form is open, **When** the user clicks to choose an image, **Then** an image selection card opens with a search input.
3. **Given** the image selection card is open, **When** the user types a search query, **Then** the list filters to show matching images from the database.
4. **Given** the user has filled in time (minutes/hours) and selected an image, **When** they save the notification, **Then** a new timer is created, becomes active, and begins counting down.

---

### User Story 2 - Toggle Sound for Custom Notification (Priority: P2)

As a user, I want to be able to enable or disable sound for my custom notifications, so I can choose whether I receive audio alerts when the timer finishes.

**Why this priority**: Users need control over audio feedback, as requested.

**Independent Test**: The user creates or edits a custom notification and toggles the "Sound" option on. When the timer reaches zero, the app plays an alert sound.

**Acceptance Scenarios**:

1. **Given** a custom notification is active with sound enabled, **When** its timer reaches zero, **Then** an audio alert plays.
2. **Given** a custom notification is active with sound disabled, **When** its timer reaches zero, **Then** the visual alert shows but no audio plays.

### Edge Cases

- What happens when there are no images available in the database?
- What happens if the user tries to create a timer with 0 minutes/hours?
- What happens to active custom timers if the application is restarted?
- What happens when multiple custom notifications reach zero at the exact same time?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to create a new custom notification in the Notifications tab.
- **FR-002**: System MUST allow users to search and select an image from the local database to associate with the notification.
- **FR-003**: System MUST allow users to specify the duration of the notification in minutes or hours.
- **FR-004**: System MUST allow users to toggle the notification as active or inactive.
- **FR-005**: System MUST allow users to toggle an audio alert (sound) on or off for the notification.
- **FR-006**: System MUST trigger a visual (and optionally audio) alert when the custom notification timer reaches zero.
- **FR-007**: System MUST allow users to manage (edit, delete) created custom notifications.

### Local Data & Settings

- **Data Location**: Custom notifications must be persisted in the local settings/database (e.g., `felb_settings.json` or equivalent local DB).
- **Failure Handling**: If the image database fails to load, the image selector should show an appropriate error or empty state.

### Localization & User-Facing Text

- **User-Facing Strings**: "Create Custom Notification", "Select Image", "Search Images", "Duration", "Minutes", "Hours", "Active", "Play Sound", "Save", "Cancel", "No images found".
- **Translation Catalogs**: All new labels and messages must be added to the supported translation files (pt/en/es/fr).

### Key Entities

- **Custom Notification**: Represents a user-defined timer alert.
  - Attributes: ID, ImageReference, Duration (seconds/minutes), IsActive, PlaySound, TimeRemaining.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can successfully create a new custom notification within 5 clicks.
- **SC-002**: Searching for an image in the image card returns results in under 500ms.
- **SC-003**: Custom notification alerts trigger exactly when the specified duration elapses.

## Assumptions

- We assume the "database" of images already exists and can be queried via an existing API or local data structure.
- We assume that "active" means the timer starts counting down immediately upon creation/saving.
- We assume standard alert sounds are used, rather than allowing users to upload custom MP3 files.
