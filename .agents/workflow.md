# GG Coalition Agent Workflow

## Purpose

This workflow describes how project-specific agents should coordinate on GG Coalition tasks. Agents are role guides, not permission bypasses. Each agent must follow the repository guardrails and the current user request.

## Default Flow

1. Read `.agents/project-context.md`.
2. Read the relevant agent guide in `.agents/agents/`.
3. Check the current user restrictions before touching files.
4. Inspect the existing implementation before proposing or editing.
5. Keep changes scoped to the requested behavior.
6. Run the smallest useful validation.
7. Report files changed, validation performed, and residual risk.

## Agent Handoff Map

- Architecture or cross-module behavior: `architect-agent`.
- QML layout, interaction, themes, and colorblind mode: `qml-ui-agent`.
- Foxhole logistics and stockpile logic: `stockpile-agent`.
- Translation coverage and locale consistency: `i18n-agent`.
- Nuitka, updater, installer, and Windows release mechanics: `updater-build-agent`.
- Regression review and validation plans: `qa-validation-agent`.
- Release journal fragments and generated localized changelogs: `release-journal-agent`.
- Stable build, release, and auto updater validation: `release-build-qa-agent`.
- User-facing release communication: `release-notes-agent`.

## Review Gates

Use `qa-validation-agent` before finishing changes that touch:

- Login, identity, or Discord OAuth2 behavior.
- Chat, stockpile, or Wiki Foxhole workflows.
- Automation features such as auto clicker, auto pilot, macros, or time task.
- Updater, installer, build scripts, or version metadata.
- Translations, themes, color system, or colorblind mode.
- Release notes, release journal fragments, or generated changelogs for a release.

## Release Journal

- Record each relevant change as a fragment in `.release/unreleased/`.
- Use `.release/templates/change-fragment-template.md` for fragment structure.
- Use `release-journal-agent` to validate fragments against git history and generate localized release notes.
- Do not delete, move, or archive fragments without explicit user authorization.

## Documentation-Only Tasks

For documentation/configuration-only work:

- Do not alter application source files.
- Do not reformat unrelated files.
- Do not modify `.agents/skills/`.
- Verify the expected files exist.
- Summarize the created files at the end.

## Escalation Rules

Ask for clarification only when a decision cannot be inferred safely from local context. Otherwise, make conservative choices aligned with the current architecture.

Request elevated command approval only when needed for filesystem access, networking, GUI execution, build execution, or destructive operations.
