---
schema_version: 1
id: GYM-109
title: "ui-i18n: frontend string catalog (en/ru) + extract hardcoded strings + 8 muscle labels"
slug: gym-109-ui-string-catalog
status: backlog
priority: medium
type: feature
labels: [i18n, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T01:00:00Z
start_date: null
finish_date: null
updated: 2026-06-10T01:00:00Z
epic: ui-i18n
depends_on: [GYM-108]
blocks: []
related: []
commits: []
tests: []
design_reports: ["docs/adr/0003-i18n-architecture.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-109 — ui-i18n: UI string catalog (Channel A)

## Problem
Channel A of [ADR 0003](../../docs/adr/0003-i18n-architecture.md): UI chrome (buttons, headings, toasts)
and the 8 fixed muscle names are hardcoded English. They must localize by the resolved locale (GYM-108).
Muscles localize HERE (frontend catalog), NOT via a DB `muscle_alias` table.

## Solution
1. Add a lightweight i18n lib + per-locale catalogs (`en.json`/`ru.json`) keyed by the GYM-108 registry.
2. Extract hardcoded strings from `apps/web` components into keys; render via the catalog + `getLocale()`.
3. Include the 8 muscle labels as a `muscles.*` namespace (API still returns canonical id/name; frontend
   maps to the localized label).
4. Must go through the `frontend-design-engineer` agent + `frontend-design` plugin (UI work per CLAUDE.md).

## Acceptance criteria
- [ ] Switching Telegram language to `ru` localizes chrome + muscle labels; `en`/unknown stays English.
- [ ] No string left hardcoded in touched components; build + typecheck green.

## Comments

### 2026-06-10T01:00:00Z — created
Self-contained frontend wave; scheduled after the foundation + exercise-search land. Does not block
GYM-93/94.
