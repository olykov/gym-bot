---
schema_version: 1
id: GYM-41
title: "apps/web: scaffold + AppShell + tokens + Telegram SDK + auth"
slug: gym-41-web-shell
status: done
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T11:10:00Z
finish_date: 2026-06-04T13:40:00Z
updated: 2026-06-04T13:40:00Z
epic: phase-5
depends_on: [GYM-38]
blocks: [GYM-42]
related: [GYM-12]
commits: [371ed5c4d054b980282bab0ee613b4250f997eec]
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

### 2026-06-04T13:40:00Z — shell + design system built (status → review)
Scaffolded `apps/web` (React 18 + TS + Vite + Tailwind), mirroring `apps/admin`'s tsconfig / vite /
tailwind / postcss / Dockerfile / nginx config. Stayed strictly inside `apps/web/`; the generated TS
client (`packages/api-contract/clients/typescript/schema.ts`, already present, gitignored) is imported
via the `@api-contract` alias and not committed.

**`frontend-design` skill invoked** at the start of the session (HARD RULE #1). The committed
**"Chalk & Iron"** direction (spec §9) was applied precisely — not re-picked.

Built, per spec section:
- **§1 stack only** — added react-router-dom, @tanstack/react-query, echarts + echarts-for-react
  (installed for GYM-42), @twa-dev/sdk; the generated TS client. No other UI kit.
- **§2 + §10.1 AppShell** — one `<AppShell>` = fixed `<AppHeader>` (Bebas title + hairline + scrim
  §9.5) + fixed `<BottomNav>` (Dashboard · Progress, ≥44px targets, sliding `--accent` indicator +
  `selectionChanged` haptic) + single `<Container>` (480px max-width, 16px padding, the only scroll
  area, top/bottom padding clearing both fixed bars + `env(safe-area-inset-*)`).
- **§3 + §9.3 tokens** — `tokens.css`: Telegram `themeParams` → CSS vars at runtime (light+dark via
  `data-theme`, with an OS-preference fallback); app-owned brand layer (`--accent` light `#E5482F` /
  dark `#FF6A4D`, `--accent-weak`, 5-step activity ramp) via `color-mix`; spacing 4/8/12/16/24/32,
  radii/shadow/type tokens, all wired into the Tailwind theme (no magic px/hex in components).
- **§9.2 fonts** — Bebas Neue + Sora self-hosted as `.woff2`, `font-display:swap`, preloaded; fallback
  stack (Bebas→Oswald, Sora→system); ~64 KB total (≤95 KB budget). No Google-Fonts critical request.
- **§4 + §9.4 Telegram SDK** — `ready()`/`expand()`, `themeChanged` + `viewportChanged` listeners,
  BackButton wiring, haptic on tab switch; all degrade to no-ops outside Telegram.
- **§4 auth** — `initData` → `/auth/telegram/webapp` (mirrors `apps/admin/src/pages/Login.tsx`) → JWT
  in memory + sessionStorage → typed fetch wrapper attaches `Bearer`; wrapped in TanStack Query.
  `<AuthGate>` shows a skeleton shell while pending, `<ErrorState>` + retry on failure.
- **§10.4 + §10.2 primitives** (token-only, built once): `Card`, `Divider`, `Skeleton`
  (+SkeletonCard/Grid/Chart), `EmptyState`, `ErrorState`, `StatCard` (+StatChip).
- **§9.4/§9.5 motion + texture** — page-load staggered reveal, press-95, shimmer, faint `feTurbulence`
  grain; ALL gated behind `prefers-reduced-motion` (and grain under reduced-transparency).
- Two placeholder routes (Dashboard 2×2 StatCards + EmptyState; Progress SkeletonChart + EmptyState)
  render inside the shell so it's demonstrable end-to-end. Real data UIs = GYM-42.

**Build:** `npm install` + `npm run build` (tsc type-check gate + vite build) — **green**.
Output: `index-*.css 12.72 kB` (gzip 3.82), `index-*.js 284 kB` (gzip 89.6), 3 woff2 in `dist/fonts/`.
Verified in built CSS: `--accent`/`--header-h` tokens, `color-mix` brand layer, `feTurbulence` grain,
`env(safe-area-inset-*)`, `prefers-reduced-motion` guard, both font families.

Not done here (deferred, correctly out of GYM-41 scope): the data pages themselves (ActivityGrid,
SummaryCards count-up, ExerciseProgressChart, the ECharts token theme) are GYM-42. Live auth
round-trip + light/dark visual pass need a real Telegram client / browser run, not possible in this
environment — the build is green and the mapping/tokens are present and self-reviewed against §7.
