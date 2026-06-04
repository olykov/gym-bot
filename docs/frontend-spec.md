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
- On load: `WebApp.ready()` → **request true fullscreen** (Bot API 8.0), read `initData` /
  `initDataUnsafe`.
- **Fullscreen (Bot API 8.0, GYM-54).** The app boots into **true fullscreen**, not just fullsize.
  On boot, after `ready()`, call `WebApp.requestFullscreen()` guarded by
  `WebApp.isVersionAtLeast('8.0')` and wrapped in try/catch; on failure / old client / desktop, **fall
  back to `WebApp.expand()`**. Subscribe to `fullscreenChanged`. The SDK is `@twa-dev/sdk` `^8.x`
  (the Bot API 8.0 surface: `requestFullscreen`, `isFullscreen`, `fullscreenChanged`, `safeAreaInset`,
  `contentSafeAreaInset`, `safeAreaChanged`, `contentSafeAreaChanged`).
- **Content safe-areas (critical in fullscreen).** In fullscreen Telegram overlays its own controls
  (close / menu) at the very top of the WebApp, so the fixed `<AppHeader>` MUST sit **below** them and
  never under the Telegram close button. On boot and on every `safeAreaChanged` /
  `contentSafeAreaChanged` / `fullscreenChanged`, read `WebApp.contentSafeAreaInset` (the area clear of
  Telegram's overlaid controls) and `WebApp.safeAreaInset` (device notch / home-indicator) and write
  them to CSS vars: `--tg-content-top`/`--tg-content-bottom` (device inset + content inset, the
  header/footer clearance) and `--tg-safe-top/bottom/left/right` (device only). The shell chrome then
  pads with **`max(env(safe-area-inset-*), var(--tg-*))`** so it clears the Telegram controls in
  fullscreen AND still respects the notch in fullsize / a plain browser:
  - `<AppHeader>` top padding = `max(env(safe-area-inset-top), var(--tg-content-top))`.
  - `<Container>` top padding adds the header height to that same max; bottom padding =
    `max(env(safe-area-inset-bottom), var(--tg-safe-bottom)) + nav height`.
  - `<BottomNav>` bottom padding = `max(env(safe-area-inset-bottom), var(--tg-safe-bottom))`.
  All vars default to `0px` outside Telegram, so the `max()` degrades to the plain `env()` values.
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
- **`<BottomNav>`** — tabs **Dashboard · Progress · History** (the History tab is added in §11;
  Distribution · Profile remain reserved/commented slots for the later iteration). Each tab = icon +
  Sora label, ≥44px touch target, active = `--accent` glyph + sliding indicator (§9.4) +
  `--accent-weak` pill. Always visible, never disappears. Respects `safe-area-inset-bottom`. At 3 tabs
  the indicator/label math is unchanged (tabs flex equally); History uses a stacked-bars/clock glyph
  distinct from Dashboard's grid and Progress's line.
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

---

## 11. History & set-editing (v1)

> Refined via the `frontend-design` plugin (2026-06-04, GYM-48). This is the *details + interaction*
> layer for the History feature; it does NOT relax any §0–§10 rule (shell, single ~480px container,
> spacing 4/8/12/16/24/32, tokens, mobile-first, Chalk & Iron). **Distinctive in the details,
> disciplined in the structure.** Scope v1: **browse trainings by day → open a day → see exercises
> with their sets → edit a set's weight/reps → delete a set.** Out of scope (v2 / GYM-51): add-set
> retroactively, move a set between exercises, multi-set bulk edit.
>
> Backing contract (`packages/api-contract/openapi.yaml`):
> `GET /training/days?from&to` → `TrainingDay[]` (`{date, muscles[], exercises_count, sets_count}`),
> `GET /training/day/{date}` → `TrainingDayDetail` (`{date, exercises[]}`, each exercise
> `{exercise_id, exercise_name, muscle_name, sets[]}`, each set `{training_id, set, weight, reps}`),
> `PUT /training/{training_id}` body `{weight, reps}` → `Training`, `DELETE /training/{training_id}`
> → 204. **The set's `training_id` is the mutation key** — carry it on every `<SetRow>`.

### 11.1 Navigation — bottom-nav becomes 3 tabs
- Tabs are now **Dashboard · Progress · History** (route `/history`). Same `<BottomNav>` contract
  (§10.1): ≥44px target, `--accent` active glyph, sliding accent indicator (§9.4), `--accent-weak`
  pill, `selectionChanged` haptic on switch, all motion behind `prefers-reduced-motion`. History glyph
  = three short stacked horizontal bars over a baseline (a "log" mark), token-stroked like the others;
  visually distinct from the Dashboard grid and the Progress line.
- Add the tab to `apps/web/src/components/shell/navConfig.tsx` (the existing reserved-slots comment
  stays; Distribution · Profile are still deferred). Routes: `/history` (day list) and
  `/history/:date` (day detail) under the same `<AppShell>` — **no page builds its own chrome.**

### 11.2 Day list (`/history`) — `<DayCard>` list from `GET /training/days`
A reverse-chronological list of **one `<DayCard>` per training day**, inside the standard
`<Container>` (16px padding, vertical rhythm). The card is a composition of the existing `<Card>`
(one card style only — no new card variant):

- **Date heading** — Bebas Neue, the hero of the row. Format human + condensed, e.g. **`MON 02 JUN`**
  (weekday + day + month, upper, tabular). The full `YYYY` is shown only when the year differs from
  the current year (keeps the 360px row tight). `--text`.
- **Muscle chips** — a wrapping row of small Sora chips from `day.muscles[]` (e.g. `Chest` `Triceps`).
  Chip = `--accent-weak` background + `--text` label, radius token, ≤2 lines then `+N` overflow chip.
  Chips are **display-only** here (not filters in v1).
- **Counts line** — Sora `--hint`, tabular-nums: `{exercises_count} exercises · {sets_count} sets`
  (singular/plural handled). This is the "what happened that day" at-a-glance.
- **Affordance** — the whole card is the tap target (≥44px tall), press → 0.98 scale 80ms (§9.4) +
  `impactOccurred('light')` haptic, navigates to `/history/:date` (`date` = `day.date`, the API's
  date string). A trailing chevron (`--hint`) signals drill-in. No per-card edit/delete here — editing
  lives in the day detail (§11.4), keeping the list a pure browse surface.

**Ordering & pagination (window-based, NOT offset).** The contract paginates by the `from`/`to`
window, mirroring the activity grid — there is no `offset/limit`. v1 default window = **last ~12 weeks**
(`to = today`, `from = today − ~84d`); list is already newest-first from the API. "Load older" =
**expand the window backward** another ~12 weeks (`from -= 84d`, same `to`) and re-query; render the
fuller list (TanStack Query caches per window key). Trigger via an **infinite-scroll sentinel**
(IntersectionObserver near the list bottom) with a manual **"Load earlier"** `<Card>`-styled button as
the non-JS/reduced-motion fallback. Stop expanding when a window returns no new earliest day (we've
reached the user's first training). Whale-user guard: the window is bounded per fetch, so a
multi-year history never loads as one unbounded list (see §11.7).

- **Query key:** `["training", "days", from, to]` (consistent with `["analytics","activity",from,to]`).
- **Loading:** `SkeletonCard` × ~5 matching the `<DayCard>` shape (a Bebas-height bar, two chip
  blocks, a hint-line) — never a spinner, never a layout shift (§10.4).
- **Empty (no trainings at all):** `<EmptyState>` — Bebas headline "NO TRAININGS YET", Sora subline
  "Log a set in the bot and it shows up here." No action button in the Mini App (logging happens in
  the bot). New-user path must not fan out extra queries (§0 / ARCH §2 "empty path is expensive").
- **Empty tail (window exhausted):** stop the sentinel, show a quiet Sora `--hint` "That's the
  beginning." footer — not an error.
- **Error:** `<ErrorState>` inline (Sora message + retry → re-runs the query).

### 11.3 Day detail (`/history/:date`) — `GET /training/day/{date}`
- **Back:** wire the Telegram **`BackButton`** (`WebApp.BackButton.show()` + `onClick → navigate(-1)`,
  hidden on unmount) so the native ← returns to the list. The `<AppHeader>` title is the day in Bebas
  (e.g. `MON 02 JUN`); the bottom-nav stays visible (History tab active) — detail is a sub-route, not
  a modal page.
- **Body:** exercises **grouped** (the API already groups by exercise). Each exercise = a `<Card>`
  with a header row — exercise name (Sora 600, `--text`) + a small muscle chip (`muscle_name`,
  `--accent-weak`) — then its sets as a column of `<SetRow>`:
  - **`<SetRow>`** — leading `Set {n}` label (Sora `--hint`), trailing the figure **`{weight}kg × {reps}`**
    where `{weight}`/`{reps}` are Bebas-leaning emphasis with `tabular-nums` so rows align and don't
    jitter. Example rendered row: **`Set 1 — 100kg × 8`**. ≥44px tall, one row style reused
    (extends the `<ListRow>` idea), `<Divider>` between rows.
  - **Tap a `<SetRow>`** → opens the **`<BottomSheet>` set editor** (§11.4) for that `training_id`,
    with `impactOccurred('light')` haptic. The row is the only edit entry point — no inline edit fields
    in the list (avoids fat-finger edits while scrolling).
  - **Swipe-left on a `<SetRow>`** reveals a `--accent` **Delete** action (the touch-native delete
    gesture); the same delete also lives inside the sheet (§11.4) so it's reachable without the gesture
    and on desktop. Both paths run the confirm in §11.4.
- **States:** `SkeletonCard` matching the exercise/set layout while loading; `<EmptyState>` "EMPTY DAY"
  if a detail somehow has no sets (e.g. the last set was just deleted — then auto-`navigate(-1)` back to
  the list after the optimistic update lands); `<ErrorState>` + retry on error; 404 → "This day has no
  trainings" empty state, not a crash.
- **Query key:** `["training", "day", date]`.

### 11.4 Set editor — `<BottomSheet>` with steppers, in-sheet sticky Save, delete + confirm
The single interaction for editing/removing a set. **Bottom-sheet** (mobile-native, thumb-reachable),
NOT a centered modal:

- **`<BottomSheet>`** — slides up from the bottom inside the shell, anchored to the bottom safe-area
  (`max(env(safe-area-inset-bottom), --tg-safe-bottom)`, §4), `--bg` surface with the §9.5 top hairline
  + grab-handle, a scrim over the page (tap-scrim or BackButton dismisses). Max-width = the container
  width (it never goes wider than the column). Slide is 240ms ease-out, **behind
  `prefers-reduced-motion`** (reduced = instant, no slide). Focus-trapped while open; `BackButton` while
  the sheet is open closes the sheet first (one back-step), not the page.
- **Sheet fit — NEVER clip (GYM-54).** The panel is capped at a `max-height` of
  `calc(100dvh − max(env(safe-area-inset-top), --tg-content-top) − ~24px margin)`, is a flex column,
  and its body region is `overflow-y:auto`. A tall sheet therefore scrolls **internally** instead of
  running off-screen, so Weight + Reps + Save + Delete are always reachable and the lowest field
  (Reps) is never clipped. The body's bottom padding clears the device / Telegram bottom inset.
- **Header:** the set's identity, read-only — `{exercise_name}` (Sora 600) + `Set {n}` (`--hint`).
  Only weight/reps are mutable (matches `TrainingUpdate`); muscle/exercise/set-number are NOT editable
  in v1 (moving a set = GYM-51).
- **Two `<Stepper>` fields** — **Weight (kg)** and **Reps**:
  - `<Stepper>` (a.k.a. `<NumberField>`) = a **−** button, a center numeric value, a **+** button; the
    value is also a tappable `<input inputmode="decimal">` (weight) / `inputmode="numeric"` (reps) so a
    user can type directly instead of tapping +/- many times. Buttons ≥44×44px, value in Bebas/tabular-
    nums (no jitter on change), generous hit area.
  - **Weight:** min 0, **step 2.5kg** on the buttons (gym-plate granularity), decimals allowed via the
    keyboard for plate-math (e.g. 102.5) — `inputmode="decimal"`, accept `.`/`,` and normalize.
  - **Reps:** min 0, integer, step 1.
  - Long-press / hold-to-repeat on ± is a nice-to-have, not required; if added it must respect reduced-
    motion (no animated ramp) and remain ≥44px.
- **Save:** an **in-sheet sticky SAVE button** (token-only, `--accent` fill per §9.3, `--button-text`
  label, ≥48px), pinned to the bottom of the sheet's scroll viewport (`position:sticky; bottom:0`)
  above the bottom safe-area, with `notificationOccurred('success')` haptic on success. Fires
  `PUT /training/{training_id}` `{weight, reps}` then closes optimistically. Save is **disabled** when
  the value is unchanged or invalid (empty / negative / non-integer reps) — same logic as before.
  > **Why in-sheet, not the native MainButton (GYM-54):** the Telegram native `MainButton` overlays the
  > WebApp viewport bottom; inside a bottom-sheet it both *covered* the sheet's lowest field and gave
  > the sheet no bottom anchor, so Reps clipped on real devices (this caused GYM-53 #1 + GYM-54). A
  > sticky in-sheet button makes the sheet self-contained, predictable, and clip-proof, and works
  > identically on desktop / old clients with no MainButton.
- **Delete:** a clearly secondary **Delete set** affordance inside the sheet (Sora label, `--accent`
  text, NOT a full red fill — accent is sparing per §9.3), separated from Save so it's not mis-tapped.
  Tapping it (or the swipe-delete in §11.3) opens a **confirm step** — an in-sheet two-button confirm
  ("Delete this set?" → **Cancel** / **Delete**) with `notificationOccurred('warning')` haptic; the
  destructive **Delete** is the accent button. Confirmed → `DELETE /training/{training_id}`.
  Two-step confirm is mandatory (fat-finger guard, §11.7).

**Optimistic update + cache invalidation (the cross-screen contract).** Both mutations are optimistic
via TanStack Query `onMutate`:
- **Edit:** snapshot, optimistically patch the set in `["training","day",date]` (and the `sets_count`
  is unchanged), close the sheet immediately. `onError` → roll back to the snapshot + show an inline
  `<ErrorState>`/toast "Couldn't save — restored." (rollback is mandatory, §11.7). `onSettled` →
  invalidate.
- **Delete:** snapshot, optimistically remove the `<SetRow>` from the day detail and decrement the
  day's `sets_count`/`exercises_count` (drop the exercise group if it was its last set); if the day is
  now empty, `navigate(-1)`. `onError` → restore. `onSettled` → invalidate.
- **Invalidate on settle (so Dashboard/Progress refresh):**
  `["training","day",date]`, `["training","days"]` (all windows), `["analytics","summary"]`,
  `["analytics","activity"]`, and `["analytics","exercise-progress"]` (a PR/weight edit can move the
  chart). Editing weight can change a PR → the Dashboard PRs card and the Progress chart must re-fetch;
  this is why summary + activity + exercise-progress are all in the invalidation set.

### 11.5 New primitives to add (token-only, reused — define them once in `apps/web/src/components/ui`)
All four are **tokens-only** (spacing 4/8/12/16/24/32, color via §3 + §9.3 vars), mobile-first at
360px, built once and reused (no per-page variants, §2). They **reuse** existing primitives where
possible: `<DayCard>` and the day-detail exercise group are compositions of `<Card>`; `<SetRow>`
extends `<ListRow>`; loading/empty/error always go through `<Skeleton>`/`<EmptyState>`/`<ErrorState>`.

- **`<BottomSheet>`** — bottom-anchored sheet (grab-handle, scrim, safe-area-bottom inset, §9.5
  hairline, reduced-motion-guarded slide, focus-trap, BackButton-to-close). Generic: it holds the set
  editor now and is reusable for any future sheet. One sheet style only.
- **`<Stepper>` / `<NumberField>`** — ≥44px ± buttons + typed numeric input, Bebas/tabular-nums value,
  configurable `min`/`step`/`inputMode`/`integer`, decimal-comma normalization. Reused for Weight and
  Reps (and any future numeric field).
- **`<DayCard>`** — the one history-row card (date heading Bebas, muscle chips, counts line, chevron,
  press state, navigates). A `<Card>` composition; reused for every day in the list.
- **`<SetRow>`** — the one set row (`Set {n}` + `{weight}kg × {reps}`, tabular-nums, ≥44px, swipe-to-
  delete, tap-to-edit). Extends `<ListRow>`; reused for every set in the day detail.
- A small **`<Chip>`** (muscle chip, `--accent-weak`/`--text`) may be extracted if not already present;
  if a chip primitive exists from §10, reuse it rather than re-defining.

### 11.6 States + motion (light + dark, reduced-motion)
- **Skeletons match layout:** day-list = `SkeletonCard`×5 shaped like `<DayCard>`; day-detail =
  exercise-group skeletons with set-row bars. No spinners, no layout shift (§10.4).
- **Empty:** no-trainings (whole list) and empty-day both use `<EmptyState>` (Bebas headline + Sora
  subline); window-exhausted uses a quiet `--hint` footer, not an empty state.
- **Error + retry:** `<ErrorState>` for query errors; mutation errors surface as the rollback
  toast/inline message (never a raw error dump).
- **Motion:** route-mount stagger of the list/day-detail children (§9.4, 0/60/120/180ms rise+fade);
  card/row press 0.98@80ms; sheet slide 240ms; **all behind `prefers-reduced-motion: reduce`** (then:
  instant opacity only, no slide/stagger/scale). **Haptics stay** (not motion): light on
  navigate/open-sheet, success on save, warning on delete-confirm, `selectionChanged` on tab switch.
- **Light + dark:** all surfaces are Telegram `themeParams`; the only app-owned colors are
  `--accent`/`--accent-weak` (§9.3), which already adapt per theme. **Verify in dark:** muscle-chip
  `--accent-weak` contrast, the `<SetRow>` divider hairline, and the bottom-sheet scrim over a
  near-black `--bg`.

### 11.7 Gaps / risks (plugin lens — concrete)
- **Fat-finger delete (highest risk):** browsing → accidental swipe/tap could destroy a set. Mitigation:
  destructive action is **never one-tap** — swipe reveals (doesn't delete), and both swipe and in-sheet
  delete route through the **two-step in-sheet confirm** (§11.4) with a warning haptic. The accent
  Delete button is spatially separated from Save.
- **Optimistic-rollback correctness:** an edit/delete that the API rejects (409/404/network) must
  visibly restore prior state. Snapshot in `onMutate`, restore in `onError`, surface a non-scary
  "couldn't save — restored" message. Must be tested for both edit and delete; a silent desync between
  the optimistic UI and the server is the worst outcome.
- **Decimal weight on mobile keyboards:** `2.5kg` plate math needs decimals, but mobile numeric
  keyboards vary (`.` vs `,`, locale). Use `inputmode="decimal"`, accept both separators, normalize to
  a dot before `PUT`; ± buttons step 2.5 so most edits need no typing at all. Reps stay integer
  (`inputmode="numeric"`). Guard against empty/`NaN`/negative before enabling Save.
- **Large day (many sets / many exercises):** a high-volume day detail could be a long scroll. v1 keeps
  it a simple scroll inside the container (acceptable); group headers are sticky-able later. No
  virtualization in v1 (YAGNI) — revisit only if a real day exceeds ~hundreds of sets.
- **Whale-user day-list pagination:** a multi-year user must not load all days at once. The window-based
  `from`/`to` fetch (default 12 weeks, expand-on-scroll) bounds every request; stop when the earliest
  window yields no new days. This is the key scalability guard and mirrors the activity-grid window
  discipline (heavy unbounded reads are the §0/ARCH §2 anti-pattern).
- **Cross-screen staleness:** a weight edit can change a PR, streak, or the activity cell. The §11.4
  invalidation set (day, days, summary, activity, exercise-progress) is mandatory so Dashboard/Progress
  never show stale numbers after an edit. Missing one key = a visible inconsistency between tabs.
- **`training_id` is the contract key, not array index:** sets are keyed by `training_id`
  (`TrainingSet.training_id`); never mutate by list position (the optimistic reorder/removal would hit
  the wrong row). Always carry `training_id` on `<SetRow>` and in the mutation.
- **BackButton ownership:** the day detail and the open bottom-sheet both want the Telegram
  `BackButton`. Define a clear stack: sheet-open → Back closes the sheet; sheet-closed on
  `/history/:date` → Back returns to the list; on `/history` → Back is hidden (bottom-nav is the nav).
  Mis-wiring double-pops or strands the user — wire show/hide on mount/unmount deterministically.
