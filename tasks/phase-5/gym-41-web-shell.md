---
schema_version: 1
id: GYM-41
title: "apps/web: scaffold + AppShell + tokens + Telegram SDK + auth"
slug: gym-41-web-shell
status: backlog
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: [GYM-38]
blocks: [GYM-42]
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-41 — apps/web: shell + design system foundation

## Problem
There is no client Mini App yet. The shell + tokens + Telegram integration + auth must exist before
any screen, and they set the consistency contract for everything after.

## Plan (owner: frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- Scaffold `apps/web` (React+Vite+TS+Tailwind), mirroring `apps/admin` config.
- Build the ONE `<AppShell>`: **fixed header + fixed bottom-nav (Dashboard · Progress) + single
  content container (max-width ~480px)**, safe-area insets, scroll model.
- Design tokens from Telegram `themeParams` (light+dark) as CSS vars + Tailwind theme; spacing scale.
- Telegram SDK (`@twa-dev/sdk`): ready/expand, theme + viewport listeners, BackButton, haptics.
- Auth: initData → Core API Mini App auth → JWT → generated TS client wired with TanStack Query.
- Pick ONE coherent aesthetic direction (via the plugin) applied across the shell.

## Acceptance criteria
- [ ] Shell renders at 360px, fixed bars never overlap content, light+dark correct.
- [ ] Auth round-trip works (initData → JWT → an authed call).
- [ ] docs/frontend-spec.md §7 checklist passes; `frontend-design` skill was invoked.

## Comments

### 2026-06-04T09:00:00Z — task created
This task defines the consistency every later screen inherits. Design-led.
