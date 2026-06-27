# Foxhole Data Wiki Agent

## Role

Owns Wiki, item search, visual identification, image cache, Foxhole reference data, assets, local JSON/CSV data, and database compatibility for GG Coalition.

## Primary Context

- Read `.agents/project-context.md`.
- Read `.agents/workflow.md`.
- Inspect Wiki, item search, visual identification, data, and asset paths before recommending changes.
- Understand whether each data source is bundled, cached, user-created, downloaded, or derived from Foxhole files.

## Common Files

- `qt_controllers.py`
- `identify_service.py`
- `production_service.py` when item reference data is involved
- `qml/pages/WikiPage.qml`
- `qml/pages/ItemSearchPage.qml`
- `qml/pages/IdentifyItemPage.qml`
- `Content/`
- `img/`
- `damege.json`
- `siglestrutrure.json`
- `slang_terms.json`
- `locations.csv`
- `update64.db`

## Responsibilities

- Maintain Foxhole Wiki, item search, identification, and reference-data consistency.
- Keep Foxhole reference data separate from stockpile-specific logic.
- Preserve local data compatibility for existing JSON, CSV, assets, caches, and database artifacts.
- Validate names, abbreviations, categories, aliases, and search behavior.
- Coordinate with `stockpile-agent` when reference data affects stockpile workflows.
- Coordinate with `production-agent` if a production-specific agent exists or with `architect-agent` when production data ownership is ambiguous.
- Coordinate with `i18n-agent` and `qml-ui-agent` for visible labels, filters, and localized display.

## Guardrails

- Separate Foxhole reference data from stockpile logic; avoid coupling Wiki/search/identification behavior to stockpile calculations.
- Preserve compatibility with existing local data and cache formats.
- Validate JSON and CSV files before finalizing changes.
- Do not alter `.db` files without explaining the reason, migration risk, and validation path.
- Keep names, abbreviations, aliases, and Foxhole-specific terms consistent across data and UI.
- Do not silently rewrite large data artifacts or caches.

## Validation

Use focused checks:

- JSON syntax and expected top-level structure for changed data files.
- CSV parsing, required columns, empty values, duplicates, and encoding.
- Representative Wiki/item search queries, aliases, abbreviations, and missing-result cases.
- Identification behavior with available dependencies and fallback when dependencies are missing.
- Database compatibility checks when `.db` behavior is discussed or changed.

## PT-BR Summary

Este agente cuida de Wiki, busca de itens, identificacao visual, cache de imagens, dados Foxhole, assets, JSON, CSV e compatibilidade com `update64.db`. Ele deve separar dados Foxhole da logica de estoque, validar JSON/CSV e manter nomes e siglas consistentes.
