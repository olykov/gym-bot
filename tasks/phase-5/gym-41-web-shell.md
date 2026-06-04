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
  content container (max-width ~480px)**, safe-area insets, scroll model. Components per spec §10.1:
  `<AppShell>`, `<AppHeader>` (Bebas title + scrim), `<BottomNav>` (sliding `--accent` indicator,
  ≥44px tabs), internal `<Container>`.
- Apply the **"Chalk & Iron"** aesthetic (spec §9): **Bebas Neue** (display/numerals) + **Sora**
  (body/labels), self-hosted `.woff2` `font-display:swap` (no Google-Fonts critical request);
  `--accent` Chalk Red layered on Telegram themeParams (light+dark); page-load staggered reveal +
  faint grain texture, all gated by `prefers-reduced-motion` / kept token-only.
- Design tokens from Telegram `themeParams` (light+dark) as CSS vars + Tailwind theme; spacing scale.
  The small app-owned brand layer (`--accent`, `--accent-weak`, activity ramp) is defined here too
  and must adapt per theme — base surface/text stay Telegram-owned (spec §9.3).
- Build the shared primitives that the shell needs now: `<Card>`, `<Divider>`, `<Skeleton>`,
  `<EmptyState>`, `<ErrorState>` (spec §10.4) so GYM-42 reuses, never re-invents, them.
- Telegram SDK (`@twa-dev/sdk`): ready/expand, theme + viewport listeners, BackButton, haptics
  (`selectionChanged` on tab switch).
- Auth: initData → Core API Mini App auth (`/auth/telegram/webapp`, mirror `apps/admin/src/pages/
  Login.tsx`) → JWT held in memory/session → generated TS client wired with TanStack Query.
- Pick ONE coherent aesthetic direction (via the plugin) applied across the shell — already committed
  as "Chalk & Iron" in spec §9; apply it, don't re-pick.

## Acceptance criteria
- [ ] Shell renders at 360px, fixed bars never overlap content, light+dark correct.
- [ ] Auth round-trip works (initData → JWT → an authed call).
- [ ] Webfonts self-hosted, `font-display:swap`, no render-block on the critical path; fallback stack
      doesn't shift layout badly on swap.
- [ ] Bottom-nav + header respect `safe-area-inset-*`; scrim/hairline present; haptic on tab switch.
- [ ] `prefers-reduced-motion: reduce` disables stagger/count-up/grain motion (verified).
- [ ] Shared primitives (`Card`/`Divider`/`Skeleton`/`EmptyState`/`ErrorState`) exist and are
      token-only.
- [ ] docs/frontend-spec.md §7 checklist passes; `frontend-design` skill was invoked.

## Comments

### 2026-06-04T09:00:00Z — task created
This task defines the consistency every later screen inherits. Design-led.
