# Frontend Spec — `apps/web` (Gym Telegram Mini App)

> Canonical, binding spec for the client web app. Every frontend agent and PR MUST follow it.
> It exists so the UI is **stable, consistent, mobile-first, and on-brand** — not a patchwork of
> different widths, paddings, and ad-hoc components. Distinctive aesthetics live in the *details*;
> the *structure* is disciplined and identical on every screen.

## 0. What this app is
- `apps/web` is **the client Telegram Mini App**, served on the **current domain**
  (`gymbot.olykov.com`). It opens **inside Telegram, on a phone, in ~99.9% of sessions.**
- It progressively replaces `apps/admin` as the Mini App. The **admin panel relocating** to its own
  domain (or being embedded later) is **backlog — explicitly out of scope here. Do not plan for it.**
- **Mobile-first is the law.** Desktop must *work*, but is a secondary concern: on desktop the app
  is the same mobile column centered on a neutral backdrop.

## 1. Tech stack — the ALLOWED list (do not add libraries outside this without a task)
- **React 18 + TypeScript + Vite** (mirror `apps/admin`).
- **Tailwind CSS** (mirror `apps/admin`) — utility-first; design tokens via CSS variables.
- **Routing:** `react-router-dom`.
- **Server state / caching:** TanStack Query (`@tanstack/react-query`) — every API read goes through
  it (loading/error/cache states); never fetch-on-every-mount.
- **Charts:** Apache **ECharts** via `echarts-for-react` (the old site's choice; responsive only).
- **Telegram Mini App SDK:** `@twa-dev/sdk` (or official `telegram-web-app.js`) — initData, theme,
  viewport, BackButton, MainButton, haptics, safe areas.
- **API access:** the **generated TypeScript client** in
  `packages/api-contract/clients/typescript/`. No `fetch` sprawl, no `axios`, no other HTTP lib.
- **FORBIDDEN:** ❌ any direct DB access (the `site_old` anti-pattern), ❌ embedding secrets,
  ❌ heavy client-side aggregation, ❌ other UI kits (MUI/Chakra/Bootstrap/shadcn/etc.) — Tailwind +
  custom components only, ❌ generic AI fonts (Inter/Roboto/Arial/system) — see §5.

## 2. The App Shell — the consistency contract (non-negotiable)
Every page renders inside ONE shared `<AppShell>`. No page builds its own chrome.

```
┌───────────────────────────┐  ← env(safe-area-inset-top)
│  Fixed Header (always)     │   title/context + optional 1 action
├───────────────────────────┤
│                            │
│   Scrollable content       │   ← ONLY this area scrolls
│   inside ONE container     │
│   (single max-width)       │
│                            │
├───────────────────────────┤
│  Fixed Bottom Nav (always) │   3–5 tabs, native mobile pattern
└───────────────────────────┘  ← env(safe-area-inset-bottom)
```

- **Fixed header** — top, visible on every page, never scrolls away. Respects `safe-area-inset-top`.
- **Fixed bottom navigation (tab bar)** — primary nav, **always visible, never disappears**, on
  every page, on mobile AND desktop. This **replaces the old burger menu** (bottom tab bar is the
  mobile-native pattern). Respects `safe-area-inset-bottom`. v1 tabs: **Dashboard · Progress**
  (later: Distribution · Profile).
- **One content container** — a single `max-width` (≈ **480px**), centered, with **one** horizontal
  padding value and **one** vertical rhythm. EVERY page uses it. No page goes full-bleed except a
  deliberate edge-to-edge element *inside* the container (e.g. a chart).
- **Scroll model** — header + bottom-nav are `position: fixed`; the content area scrolls between
  them. Account for both heights with padding so content is never hidden under the fixed bars.
- **One divider style**, one card style, one list-row style — defined as components, reused. No
  ad-hoc borders/spacings per page.

## 3. Design tokens (CSS variables → Tailwind theme)
- **Telegram theme is the source of truth for color.** On load and on `themeChanged`, map
  `WebApp.themeParams` → CSS variables:
  `--bg`, `--text`, `--hint`, `--link`, `--button`, `--button-text`, `--secondary-bg`.
  Support **light AND dark automatically** (Telegram controls which). Provide a sane fallback palette
  for when the app is opened outside Telegram.
- **Spacing scale (only these):** 4, 8, 12, 16, 24, 32. No magic numbers.
- **Radii / shadows / typography scale:** tokens only.
- **Safe areas:** use `env(safe-area-inset-*)` for the fixed header/footer.

## 4. Telegram Mini App integration (mandatory)
- On load: `WebApp.ready()` → `WebApp.expand()`; read `initData` / `initDataUnsafe`.
- **Auth:** POST `initData` → Core API Mini App auth (`verify_telegram_webapp_auth` path) → JWT held
  in memory/session; the generated client sends it. Reuse the `apps/admin` pattern. RLS then scopes
  all data to the caller automatically (fail-closed).
- **Theme:** subscribe to `themeChanged`; apply `themeParams` to the CSS vars.
- **Viewport:** handle `viewportChanged` / `viewportStableHeight` so the fixed shell stays correct.
- **BackButton** for in-app back where natural; **haptics** on key actions.

## 5. Aesthetic mandate — the `frontend-design` plugin (100% mandatory)
- The **`frontend-design` skill MUST be invoked** (Skill tool) at the start of every UI design task
  — building a screen, a component, the token system, or restyling. It guides distinctive
  typography, cohesive color, purposeful motion, and the polish that avoids generic AI aesthetics.
- **Reconciliation (critical):** `frontend-design` pushes *bold, distinctive* craft; THIS spec
  demands *structural consistency*. Both hold at once:
  - **Distinctive in the details** — typography (a characterful display font + refined body font,
    never Inter/Roboto/system), color accents from a committed palette, micro-motion, texture/depth.
  - **Disciplined in the structure** — the fixed shell, the single container, the spacing scale, the
    bottom-nav, mobile-first. Never break the shell for a "creative" layout.
- Pick ONE coherent aesthetic direction for the whole app and apply it everywhere. No per-page drift.

## 6. Mobile-first rules
- Design at **360–430px** width first. Touch targets **≥ 44px**. No hover-only affordances.
- Primary actions reachable in the bottom third. Charts responsive to container width, legible at
  small sizes.
- Desktop = the same column centered; do not build separate desktop layouts.

## 7. Definition-of-done checklist (every page/PR)
- [ ] Renders inside the shared `<AppShell>` (fixed header + bottom nav + single container).
- [ ] Same container max-width + padding as every other page.
- [ ] Tokens only — no magic px / hard-coded colors.
- [ ] Verified at 360px width; safe-area insets respected; fixed bars never overlap content.
- [ ] Telegram light & dark themes both look correct.
- [ ] Data only via the generated client + TanStack Query (cached, no fetch storms).
- [ ] `frontend-design` skill was invoked for the design pass.
- [ ] No new library outside §1.

## 8. Pointers
- Target architecture & legacy-site lesson: `docs/ARCHITECTURE.md`.
- Phase 5 plan & tasks: `tasks/roadmap/gym-12-rebuild-website.md`, `tasks/phase-5/`.
- API contract & TS client: `packages/api-contract/`.
- Owning agent: `frontend-design-engineer` (mandated to use this spec + the `frontend-design` skill).

---

## 9. Concrete design direction (v1) — "Chalk & Iron"

> Refined via the `frontend-design` plugin (2026-06-04). This is the committed aesthetic for the whole
> app. It is the *details layer* of §0–§8; it does NOT relax any structural rule (shell, container,
> spacing scale, tokens, mobile-first). **Distinctive in the details, disciplined in the structure.**

### 9.1 Concept
**"Chalk & Iron"** — a gym-floor athletic-data aesthetic: the precision of a training log on the
weight of cast iron, with the dusty energy of chalked hands. Numbers are the heroes (this is an
analytics app), set in a confident condensed display face; the body voice is quiet and legible.
Surfaces read like brushed/cast metal under Telegram's own light, with a single decisive lifting-red
accent. The opposite of the old generic "blue gradient on white" site.

Why this and not generic: it is *content-true* (an athlete tracking iron), it leans into NUMBERS
(big, condensed, tabular) which is exactly what a gym analytics app is about, and it gives one
memorable thing — the "chalk-red" PR/accent moment — without ever fighting Telegram's chrome.

### 9.2 Typography (the signature — never Inter/Roboto/Arial/system)
- **Display / numerals:** **Bebas Neue** — a tall, condensed, all-caps grotesque. Used for stat-card
  numbers, the activity-grid streak count, headers, axis-free big figures, tab/section titles.
  Condensed = big numbers fit a 360px column without wrapping. This is the brand voice.
- **Body / UI / data labels:** **Sora** — a geometric humanist sans with real character (open
  apertures, slightly quirky), excellent at small sizes for labels, list rows, tooltips, chart
  legends. Refined, not generic; pairs cleanly under Bebas Neue.
- **Numeric tables / chart tick labels:** use Sora with `font-variant-numeric: tabular-nums` so
  weights/dates align in columns and don't jitter on hover.
- **Loading strategy (mobile-critical):** self-host both as **`.woff2`, `font-display: swap`**,
  `preconnect`/`preload` only the two weights actually used (Bebas Neue 400; Sora 400 + 600). No
  Google Fonts runtime CSS request on the critical path. Fallback stack: Bebas → `"Oswald",
  ui-sans-serif` (still condensed) so the swap is not jarring; Sora → `ui-sans-serif, system-ui`.
  Total added webfont budget target **≤ ~95 KB** over the wire.

### 9.3 Color system — accent LAYERED on Telegram themeParams
Telegram `themeParams` remain the **source of truth** for base surface/text (§3): `--bg`, `--text`,
`--hint`, `--link`, `--button`, `--button-text`, `--secondary-bg` are mapped on load and on
`themeChanged`, and the app inherits the user's light/dark automatically. On top of that base we
layer a small, fixed **brand layer** that does NOT come from Telegram (so the brand survives any
theme), tuned for contrast in both modes:

- **`--accent` (Chalk Red):** light `#E5482F`, dark `#FF6A4D`. The single decisive accent — PRs,
  the active tab indicator, the "today" cell ring, primary chart line, key numbers. Used sparingly
  (a dominant-neutral / sharp-accent palette, per the plugin), never as a fill across whole cards.
- **`--accent-weak`:** `color-mix(in srgb, var(--accent) 14%, transparent)` for accent backgrounds
  (active-tab pill, PR chip) so it reads in both themes without a second hardcoded color.
- **Activity-grid scale (chalk → iron):** a 5-step ramp keyed to the *accent*, NOT GitHub green, so
  the grid is on-brand:
  - empty: `var(--secondary-bg)` with a 1px `--hint`-at-12% border;
  - L1–L4: `color-mix(in srgb, var(--accent) {18,40,68,100}%, var(--secondary-bg))`.
  - Dark mode: same `color-mix` but the empty cell is `#ffffff` at 4% over `--bg` so empty squares
    stay visible on a near-black Telegram dark background. **Verify empty-cell contrast in dark.**
- **Surfaces / depth:** cards are `--bg` raised over a `--secondary-bg` page, separated by a single
  hairline (`--hint` at 10–12%) + one soft shadow token — NOT heavy Material elevation. One card
  style only (§2).
- **`--accent` on text — a11y rule:** the accent is for **large** numerals/headlines (Bebas, ≥24px,
  needs ≥3:1) and **graphical** marks (tab glyph, ring, chart line, chip). For **small** label/body
  text use `--text`/`--hint`, never `--accent` (it won't clear 4.5:1 on `--bg` in both themes).
- **Never** introduce a purple gradient, a second accent hue, or per-page colors. One accent, period.

### 9.4 Motion language
- **Page-load reveal (the one orchestrated moment):** on each route mount, the content container's
  direct children (header block, then each card / the grid / the chart) fade+rise 8px with a
  **staggered `animation-delay`** (0 / 60 / 120 / 180 ms), ~240 ms ease-out. One tasteful entrance,
  not scattered effects.
- **Activity grid:** cells do a fast staggered "ink-in" (opacity 0→1 over columns) on first paint
  only (skip on re-render / when cached).
- **Numbers:** stat-card figures **count up** from 0 to value once on first load (~500 ms,
  ease-out), giving the Bebas numerals a moment. Skip on cache hit.
- **Micro-interactions:** tab change → Telegram **haptic** `selectionChanged` + active-indicator
  slides under the new tab (transform, 180 ms). Card/grid-cell press → 0.98 scale, 80 ms. PR chip →
  a single subtle accent pulse on appear.
- **`prefers-reduced-motion: reduce` (mandatory):** disable count-up, ink-in, stagger, slide; keep
  only instant opacity. All motion lives behind this guard. Haptics remain (not motion).

### 9.5 Texture / depth (atmosphere, not noise)
- A **very faint grain/noise overlay** (SVG `feTurbulence`, ~2–3% opacity, fixed, `pointer-events:
  none`) on the page background only — the "chalk dust" texture. Cheap, themes-agnostic, gives the
  flat Telegram surface life. Off under `prefers-reduced-transparency` if detectable.
- Depth via **one** shadow token + hairline dividers, never stacked Material shadows.
- The fixed header gets a 1px bottom hairline + a 6px `--bg`→transparent gradient scrim so scrolled
  content dissolves under it (not a hard cut). Same idea above the bottom-nav.

### 9.6 What this direction must NOT do (guardrails)
- Not break the fixed shell, the single ~480px container, the spacing scale, or tokens (§2–§3).
- Not hardcode base surface/text colors — those are Telegram's (§3). Only the small brand layer
  (`--accent*`, grid ramp, grain) is app-owned, and it adapts per light/dark.
- Not add a font/animation/charting library beyond §1. Bebas Neue + Sora are *assets*, not libraries.

---

## 10. Component inventory (MVP)

Every component below is **token-only** (spacing 4/8/12/16/24/32; color via the §3 + §9.3 vars),
mobile-first at 360px, and lives inside the one `<AppShell>`. Shared primitives are built **once** and
reused — no per-page borders/cards/spacings (§2).

### 10.1 AppShell parts
- **`<AppShell>`** — fixed header + fixed bottom-nav + one scrollable container (~480px max-width,
  one horizontal padding = 16, one vertical rhythm). Owns the scroll model and safe-area padding
  (`env(safe-area-inset-top/bottom)`), and the page-load stagger wrapper (§9.4).
- **`<AppHeader>`** — title (Bebas Neue) + optional single action slot + optional Telegram
  `BackButton` wiring. Bottom hairline + scrim (§9.5). Respects `safe-area-inset-top`. Height is a
  token; container top-padding accounts for it.
- **`<BottomNav>`** — v1 tabs **Dashboard · Progress** (reserve slots for Distribution · Profile).
  Each tab = icon + Sora label, ≥44px touch target, active = `--accent` glyph + sliding indicator
  (§9.4) + `--accent-weak` pill. Always visible, never disappears. Respects `safe-area-inset-bottom`.
- **`<Container>`** (internal to AppShell) — the single max-width column; the ONLY place page content
  mounts. No page sets its own width/padding.

### 10.2 Dashboard components
- **`<ActivityGrid>`** — GitHub-style 7×N grid, **Monday-first** (mirror site_old), chalk→iron
  accent ramp (§9.3), one cell `title`/tooltip ("N sets on <date>"), "today" cell gets an `--accent`
  ring. **MVP window = the last ~26 weeks (6 months)** — this fits the 360px container WITHOUT any
  horizontal scroll at ~9–10px cells (26 × ~11px ≈ 286px < ~328px usable), and matches site_old's
  6-month view. **No in-card scroll in v1.** A full-year view is a deferred iteration (it would need
  the single sanctioned in-card horizontal scroll, §2). The `from`/`to` query is set to that 26-week
  window. Light + dark ramps both defined; **empty-cell visibility verified in dark**. Less/More
  legend in Sora. Data: `GET /analytics/activity?from&to` via TanStack Query.
- **`<SummaryCards>`** — a **2×2 grid** of `<StatCard>` (mirror site_old's 4 numbers): **Exercises ·
  Sets · PRs · Streak** (from `/analytics/summary`). Big Bebas Neue numeral (count-up, §9.4) + Sora
  label; **PRs card** uses the `--accent` numeral + a small PR chip to make it the hero. One card
  style only.
- **`<StatCard>`** — primitive: number slot (Bebas, tabular-nums), label slot (Sora `--hint`),
  optional accent flag. Reused for all four.

### 10.3 Progress (exercise-chart) components
- **`<MusclePicker>` / `<ExercisePicker>`** — two dependent selectors (muscle → exercise) built from
  the existing list endpoints. Native-feeling: a horizontally scrollable **chip row** or a Telegram-
  style select; ≥44px targets; selection drives the query. Loading = skeleton chips.
- **`<ExerciseProgressChart>`** — `echarts-for-react`, line series of weight/reps over time, **one
  series per set** (Set 1, Set 2 …), responsive to container width, legible at 360px. **ECharts
  theming bound to tokens** (§10.5). Data: `GET /analytics/exercise-progress?muscle&exercise`.
  Toolbox/dataZoom kept minimal on mobile (pan/zoom only if it doesn't crowd the 360px frame).

### 10.4 Shared primitives (build once, reuse everywhere)
- **`<Card>`** — the one card style: `--bg` surface, hairline + single shadow token, radius token,
  padding token. No other card variants.
- **`<ListRow>`** — the one list-row: leading icon/label (Sora), trailing value (Sora tabular-nums),
  consistent height + press state. For any future list.
- **`<Divider>`** — the one divider: 1px `--hint`@12%. No ad-hoc borders.
- **`<EmptyState>`** — icon + Bebas headline + Sora subline + optional action. Used by the dashboard
  (new user, no trainings) and the chart (no data for the picked exercise). **Required on every data
  surface** — new users are the most common first-run and must never see a blank/broken screen (and
  must never trigger extra queries — the §0/ARCH §2 "empty path is the most expensive" lesson).
- **`<Skeleton>`** — token-driven shimmer block; composed into `SkeletonCard`, `SkeletonGrid`
  (grey activity squares), `SkeletonChart`. **Every TanStack Query `isLoading` renders a skeleton**,
  never a layout-shifting spinner; the skeleton matches the final layout so there's no jump.
- **`<ErrorState>`** — one inline error surface (Sora message + retry) for query `isError`; retry
  re-runs the query. No raw error dumps in the client UI.

### 10.5 ECharts theming contract (tokens, not hardcoded hex)
- Build a single `echartsTheme(cssVars)` helper read from the live CSS variables so the chart
  re-themes with Telegram light/dark automatically (re-init / `setOption` on `themeChanged`).
- **Series → tokens:** primary set line = `--accent`; subsequent sets = a small fixed token ramp
  derived from `--accent` via `color-mix` (e.g. accent, accent@70% toward `--hint`, accent@45%) so
  multi-set stays on-brand and **distinguishable in dark mode**. Cap distinct series colors; beyond
  ~4 sets, vary dash style too (a11y: don't rely on color alone).
- Axis line/labels = `--hint`; split-lines = `--hint`@10%; text = `--text`, **Sora, tabular-nums**;
  background transparent (inherits the card). Tooltip uses `--bg`/`--text`, not ECharts default white
  (which is invisible/jarring in dark mode). **Verify chart line + tooltip contrast in dark.**
- Responsive: `echarts-for-react` with a resize observer on the card; min legible font size enforced
  at 360px; legend wraps/scrolls rather than overflowing the container.
