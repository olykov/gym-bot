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

---

## 12. Record training (nav + log flow)

> Refined via the `frontend-design` plugin (2026-06-05, GYM-65, ultrathink). This is the *details +
> interaction* layer for **recording a training inside the Mini App** — it does NOT relax any §0–§11
> rule (shell, single ~480px container, spacing 4/8/12/16/24/32, tokens, mobile-first, Chalk & Iron).
> **Distinctive in the details, disciplined in the structure.** Scope: (a) the bottom-nav grows to a
> **5-item Instagram-style bar with a raised center `+`**, and (b) a **super-smooth record flow** that
> logs a workout in far fewer taps than the bot. The bot stays; the Mini App becomes a first-class
> logger.
>
> **Design north star.** Gym logging is repetitive: the same few exercises, set after set, at weights
> close to last time. The whole flow is tuned so the *second set onward costs ~1 tap*. The hero
> interaction is **pre-fill** (weight/reps already filled from the user's own history) + **auto-advance**
> (Save a set → the panel re-arms for the next set, same pre-fill, set-number incremented). Everything
> else is a fallback for the cold path (first ever set, new exercise).
>
> Backing contract (all RLS-scoped, exist today — `packages/api-contract/openapi.yaml`):
> `POST /training` (`TrainingCreate {muscle_name, exercise_name, set, weight, reps}` → `Training`),
> `GET /analytics/top-muscles` → `TopMuscle[]` (`{name, frequency}`),
> `GET /analytics/top-exercises?muscle&limit` → `TopExercise[]` (`{name, frequency}`),
> `GET /analytics/completed-sets?muscle&exercise&date` → `CompletedSets {sets:int[]}` (auto next set #),
> `GET /analytics/personal-record?muscle&exercise` → `PersonalRecord | null` (`{weight, reps, date}`),
> `GET /analytics/max-reps?muscle&exercise&weight` → `MaxReps {max_reps}` (reps pre-fill at a weight),
> `GET /muscles` + `GET /muscles/{id}/exercises` (browse fallback),
> `POST /muscles` (`MuscleCreate {name}`) + `POST /exercises` (`ExerciseCreate {name, muscle_name}`)
> (add-inline). The one thing the contract does NOT have is a **cross-muscle "recent exercises"** read
> and a **"last set" pre-fill** read — the MVP is designed to work fully without them, and §12.7 flags
> them as a small, separate nice-to-have.

### 12.1 Bottom-nav becomes 5 items with a raised center FAB
The bar grows from 3 route-tabs to **4 route-tabs + 1 center action** (Instagram pattern: feed-ish
tabs left, a publish `+` dead-center, profile far-right):

```
┌───────────────────────────────────────────────┐
│  Dashboard   Progress   ( + )   History  Profile│   ← the bar (h-nav, fixed)
│     ▢          ⌁          ●        ☰       ◔     │       ● = raised orange circle FAB
└──────────────────────────────●─────────────────┘
                          (lifted above the bar)
```

- **Route tabs (4):** `Dashboard · Progress · History · Profile`. Same `<BottomNav>` tab contract
  (§10.1): icon + Sora label, ≥44px target, active = `--accent` glyph + `--accent-weak` pill, sliding
  indicator (§9.4), `selectionChanged` haptic on switch, all motion behind `prefers-reduced-motion`.
- **Center item (1) — the FAB, an ACTION not a route.** A new `<NavFab>`: a **circular, `--accent`
  (Chalk Red — NOTE the operator says "orange"; the committed Chalk & Iron accent IS the warm
  orange-red `--accent`, so the FAB uses `--accent`, NOT a new hue — §9.3 "one accent, period"),
  raised** button sitting in the center slot, **elevated above the bar's top edge** (`translateY` up by
  ~`16px`, the bar reserves the center slot's width but renders no tab there). A bold `+` glyph in
  `--button-text`, one shadow token for the lift, a 1px `--bg` ring so it reads as a distinct shape
  against the bar. ≥56px diameter (a comfortable thumb CTA, larger than the 44px tabs — it must *stand
  out as THE primary action*). Tap → `impactOccurred('medium')` haptic + opens the **record sheet**
  (§12.2); it does **not** navigate, has no active/route state, and is never "selected".
- **The sliding active-indicator covers only the 4 route tabs, skipping the center.** Current math
  (`width = 100/tabCount`, `translateX = activeIndex * 100%`, §9.4 `BottomNav.tsx`) assumes equal
  flex tabs and breaks with a non-tab center slot. Fix: the bar is a 5-slot flex where the **center
  slot is a fixed-width spacer** (the FAB is absolutely positioned/over it), and the indicator is
  computed over the **route tabs only** — index map `{Dashboard:0, Progress:1, History:2, Profile:3}`,
  and the indicator's `translateX` accounts for the center gap (i.e. the 2 right tabs are offset by one
  slot). Concretely: render the 4 tabs in their visual order with the spacer between index 1 and 2; the
  indicator width = `(100% − centerSlotWidth) / 4` and its X position is the active tab's measured left
  edge (use a `ref`-measured offset rather than a naive `index * 100%`, since the slots are no longer
  uniform). Center tap never moves the indicator.
- **Shell contract preserved (§2 / §10.1):** the bar stays `position:fixed`, full-width, `border-t`,
  `bg-bg`, bottom padding `max(env(safe-area-inset-bottom), var(--tg-safe-bottom))`. The raised FAB's
  lift must NOT escape the safe-area: the circle's lifted top may rise above the bar, but its tap area
  and the bar's own bottom inset are unchanged, so on a notched / home-indicator device the FAB never
  collides with the home indicator (the bar already pads for it; the FAB lifts *upward*, into content
  space, not downward). See §12.8 safe-area note.
- **`navConfig.tsx` change:** add `History` (already present from §11) + a new `Profile` tab; the
  center `+` is **not** a `NavTab` (it's not a route) — it's a distinct `centerAction` rendered by
  `<BottomNav>` between tab index 1 and 2. The old "reserved slots" comment is resolved: Profile is now
  a real (stub) tab; Distribution remains deferred/commented.
- **Profile tab = a STUB route, designed as a slot only.** Route `/profile` renders inside the same
  `<AppShell>` (no own chrome) and shows a single `<EmptyState>` — Bebas headline "PROFILE", Sora
  subline "Coming soon." No data fetch (the empty path fires zero queries, §0 / ARCH §2). Glyph =
  a simple person mark (head + shoulders), token-stroked, distinct from the other three. **We design
  the slot, not the screen** — the actual profile feature is a separate task.

### 12.2 Record flow — structure (one `<BottomSheet>`, two phases)
Tapping `+` opens **one `<BottomSheet>`** (reuse the §11.4/§11.5 primitive — bottom-anchored,
grab-handle, scrim, safe-area-bottom, BackButton-closes-sheet-first, 240ms slide behind
`prefers-reduced-motion`). The sheet is a small **two-phase** machine, NOT a wizard with many screens.

**GYM-74: The sheet is `fixedHeight` (never jumps between Phase A steps).**
The panel height is fixed at `calc(100dvh − max(safe-area-top, --tg-content-top) − var(--header-h) − 24px)`,
ensuring the sheet's top edge always sits at least `--header-h + 24px` below the device/Telegram top
inset — it **never overlaps the AppShell fixed header**. Both Phase A steps (muscles / exercises) and
Phase B all occupy this same fixed height; only the body scrolls internally per step.

```
  +  ──▶  [ Phase A: PICK EXERCISE ]  ──pick──▶  [ Phase B: LOG SETS ]  ──"Done"──▶  close
                  ▲                                     │
                  └──────── "Switch exercise" ──────────┘
```

- **Phase A — exercise picker** (`<RecordPicker>`, v3 — GYM-72 restructure + GYM-74 slide-nav).
  Header "RECORD" (Bebas). The old 8-item "Recent" fast lane is **removed** — just-logged exercises
  aren't what you want next. The picker has **two in-sheet steps as a horizontal PUSH** (no sheet
  open/close, no height jump):

  **Step 1 — muscle step (default):**
  1. **Continue tile (the hot path).** A single full-width tile = the **last exercise trained TODAY**,
     derived client-side from `GET /training/day/{today}` (the exercise group whose set has the highest
     `training_id`, i.e. the most recently logged). It reuses the tile language (rounded-lg, hairline,
     `--secondary-bg`, `press-95`): a quiet "CONTINUE TODAY" eyebrow (Sora `--hint`), the
     `exercise_name` in `--text`, the `muscle_name` in `--hint`, and a trailing chevron (drill-in
     grammar, mirrors `<DayCard>`). Tap → **Phase B** immediately. **If nothing was trained today the
     tile is omitted entirely** (no empty placeholder).
  2. **A very light, fading divider** below the Continue tile — an **inset hairline masked to
     transparent at both ends** (`.record-divider-faint`, a horizontal `--hairline` gradient, width
     ~2/3, centered). It is deliberately softer than the canonical `<Divider>` hard cut: a whisper of
     separation per the operator ("совсем лёгкий, ненавязчивый"). **Only rendered when the Continue tile
     is present** (token-only, no magic colour; the §9.5 "dissolve" idea at micro scale).
  3. **Muscle tile grid.** Muscles (`top-muscles` frequency order first, then any remaining from
     `/muscles`) as an **auto-fit responsive grid** (`repeat(auto-fill, minmax(100px, 1fr))`) — NOT a
     hardcoded 3-column layout. This handles variable-length labels and custom muscles without breaking.
     Tile min height ≥ 64px. Picking a muscle **slides LEFT** to Step 2.

  **Step 2 — exercise step (slide-in from right):**
  Tapping a muscle tile triggers a **horizontal push** — the muscle panel translates out to the left
  and the exercise panel translates in from the right. Animation: `translateX(-50%)` on a 200%-wide
  flex track, `200ms ease-out-soft`, **`prefers-reduced-motion` → instant** (no transition). A **"←
  {Muscle name}"** back control at the top of Step 2 slides back; the **Telegram BackButton** (wired
  via `onBackOverride` on `<BottomSheet>`) also steps back (Step 2 → Step 1 → close). Exercise tiles
  in the same tile language (≥64px, auto-fit grid) — top ~6 + "Show all" (§12.9). **`+ Muscle`** in
  the muscle grid and **`+ Exercise`** under the exercise tiles open inline add fields.

  4. **Add inline.** A `+ Muscle` tile in the muscle grid and a `+ Exercise` affordance under the
     exercise tiles open a tiny inline text field (in-sheet, not a new screen) → on submit
     `POST /muscles` / `POST /exercises {name, muscle_name}`, optimistically insert + **auto-select into
     Phase B**. (`POST /exercises` creates the muscle if needed, per contract.) Brand-new users with no
     training today and an empty catalog land on the "ADD YOUR FIRST EXERCISE" prompt (§12.6).

- **Phase B — set-logging panel** (`<SetLogger>`, §12.3): the heart. The same sheet *swaps its body*
  to the logger (no nav, no new route, no re-open). A back-affordance ("← Switch exercise", small, top-
  left of the panel) returns to Phase A (muscle step) while keeping the sheet open. "Done" / scrim /
  BackButton closes the whole sheet.

> **Why one sheet with a body-swap, not multi-screen:** keeps the user in a single thumb-zone surface,
> preserves the §11.4 "in-sheet sticky Save, never the Telegram MainButton" decision (clip-proof on
> real devices, GYM-54), and makes auto-advance feel like staying in place rather than navigating.

### 12.3 The set-logging panel (`<SetLogger>`) — the smooth core
For the chosen `{muscle_name, exercise_name}`, the panel is built to make **each set ~1 tap**:

```
 ┌─────────────────────────────────────────────┐
 │ ← Switch exercise                            │
 │ BENCH PRESS            · Chest                │   ← exercise identity (Bebas + muscle Chip)
 │                                              │
 │ TODAY                                        │
 │  Set 1 — 100kg × 8     Set 2 — 100kg × 7     │   ← already-logged sets today (log-context)
 │                                              │
 │ SET 3                       PR 102.5kg × 5   │   ← auto set #, PR target chip (--accent)
 │  WEIGHT                 REPS                  │
 │  [ − ] [ 100.0 kg ] [+] [ − ] [ 8 ] [+]      │   ← two big <Stepper>s, PRE-FILLED
 │                                              │
 │  ┌─────────────────────────────────────────┐ │
 │  │             SAVE SET                     │ │   ← in-sheet sticky Save (--accent), §11.4
 │  └─────────────────────────────────────────┘ │
 │  Done                                        │   ← quiet secondary "finish" affordance
 └─────────────────────────────────────────────┘
```

- **Exercise identity (read-only):** `{exercise_name}` in Bebas + a muscle `<Chip>` (`--accent-weak`).
- **One read powers Phase B (perf, §12.5):** `GET /analytics/log-context?muscle&exercise&date=today`
  (GYM-71) returns `{completed_sets:int[], last_session_sets:[{set,weight,reps}], pr:{weight,reps,date}
  |null}` in **one round-trip** — it replaces the old three reads (`completed-sets` + `personal-record`
  + the recent pre-fill).
- **"Today" recap (GYM-74 fix):** a compact, tabular row/grid of sets already logged today for this
  exercise, using `<SetRow>`-style figures (`Set n — {w}kg × {r}`). Source — three tiers, in priority:
  1. **This-session sets** (optimistic, exact weight/reps just logged).
  2. **`GET /training/day/{today}` `TrainingDayExercise.sets`** (the server's already-recorded sets for
     this exercise, carrying `{set, weight, reps}`). This data is already fetched/prefetched for the
     Continue tile; filtering to the chosen exercise and passing it to `<SetLogger>` as `serverSets`
     means the recap shows real `w×r` **even after reopen or Continue** — not just `Set n ✓`.
  3. **`log-context.completed_sets`** (set numbers only, no w×r — fallback `Set n ✓` when neither tier
     1 nor tier 2 provides weight+reps for a set number).
  Session set wins over server set for the same set number (it's always more recent). This approach
  requires NO API change. The recap makes "where am I" obvious and removes the bot's "pick set number"
  step entirely.
- **Auto set-number:** `nextSet = max(log-context.completed_sets ∪ this-session sets) + 1` (so it's
  correct even mid-session and after the §11 history edits). Shown as the panel's "SET {n}" heading —
  the user **never picks a set number** (the bot's step 3 is gone).
- **Pre-filled `<Stepper>`s (the magic):** two big steppers, reusing §11.5 `<Stepper>`:
  - **Weight** — `min 0, step 2.5, inputmode="decimal"`, unit `kg`, tabular Bebas value (§11.4 plate
    granularity, decimal-comma normalized).
  - **Reps** — `min 0, step 1, integer, inputmode="numeric"`.
  - **Pre-fill rules (GYM-72 — last-session, NOT PR), in priority order for set N:**
    1. **Same session, same exercise:** pre-fill weight+reps from **the last set the user just logged
       this session** for this exercise (held in sheet state). The dominant in-workout case; no network
       call → truly ~1 tap (just Save).
    2. **Last session, set N:** pre-fill from `log-context.last_session_sets` matched on the **same set
       number** (`{set,weight,reps}` for `set === nextSet`) — i.e. *the weight/reps you did for that
       exact set last session*. This is the literal last working set, far better than the old PR anchor.
       Recomputed after each save (nextSet advances → the next last-session set fills).
    3. **No match (new exercise / no prior session set N):** empty fields with `--hint` placeholders
       ("kg" / "reps"), **Save disabled until both are valid**.
    > **The PR is NOT a pre-fill source anymore (operator feedback).** A pre-filled PR weight is the
    > wrong anchor (it's your heaviest, not your working weight); `last_session_sets` gives the actual
    > last working set per set-number, which is what you'll repeat. The PR now only labels the target
    > chip below.
  - **PR target chip:** when `log-context.pr` exists, show a small **`PR {weight}kg × {reps}`** chip
    (`--accent` text, graphical accent use, a11y-OK §9.3) by the SET heading, so the user sees the bar
    to beat. (A session PR with no reps source drops the `× {reps}` part.)
- **Save set (in-sheet sticky, §11.4 — NOT the Telegram MainButton):** a sticky `--accent`-fill button
  (`--button-text` label, ≥48px), pinned at the bottom of the sheet's scroll viewport above the bottom
  safe-area. Disabled when weight/reps are empty/invalid (negative, `NaN`, non-integer reps). On tap:
  `POST /training {muscle_name, exercise_name, set: nextSet, weight, reps}`.
- **Auto-advance (the loop):** on a successful `POST`:
  1. `notificationOccurred('success')` haptic.
  2. Append the set to the "Today" recap (optimistic, full `w×r`).
  3. **Re-arm the panel for the next set in place** — `nextSet += 1`, **keep the same weight/reps
     pre-filled** (the just-logged values; gym sets repeat), Save re-enabled. No sheet close, no
     scroll-jump (the panel stays anchored; the recap grows above). The user can Save again immediately
     → **+1 tap per additional set**. (Reduced-motion: the recap append is an instant insert, no slide.)
  4. **PR-beat celebration:** if the saved `weight` strictly exceeds the known `PersonalRecord.weight`
     (or any weight when none existed), fire the §9.4 single accent pulse on the SET/PR chip +
     `notificationOccurred('success')` (already fired) — a brief `--accent` flare on the recap row, no
     confetti, no library, behind `prefers-reduced-motion` (then: the PR chip just flips to the new
     value, no flare). Update the local PR anchor so a second PR in the session also celebrates.
- **Switch exercise / Done:**
  - **"← Switch exercise"** → body-swaps back to Phase A (sheet stays open), session recap for the
    previous exercise is preserved in cache.
  - **"Done"** (quiet secondary, Sora `--hint`) and the scrim / BackButton both **close the sheet**.
    Closing triggers the cross-screen invalidation set (§12.5) so Dashboard/Progress/History refresh.

**Tap-count budget (the acceptance bar):**
| Scenario | Taps | Breakdown |
|---|---|---|
| Open the flow | 1 | the `+` FAB |
| Continue today's last exercise | +1 | tap the Continue tile (1) — pre-filled from last-session set 1 |
| First set of an exercise (browse) | +3 | muscle tile (1) → exercise tile (1) → SAVE (1) *(pre-filled from last session)* |
| **Each additional set, same exercise** | **+1** | **SAVE** *(set #, weight, reps all pre-filled)* |
| Adjust weight by one plate then save | +2 | `+`/`−` 2.5kg (1) → SAVE (1) |
| Switch to another frequent exercise | +1 | its chip (Phase A is one back-tap away) |
> A full "3 exercises × 4 sets" workout on the hot path ≈ `1 (open) + 3×(1 pick + 4 saves)` ≈ **16 taps**
> vs the bot's `3 × 4 × 5 picks` = **60 picks**. ~1 tap per set is met for the repeat case.

### 12.4 New primitives (token-only, reuse §10/§11 first)
All token-only (spacing 4/8/12/16/24/32, color via §3+§9.3), mobile-first at 360px, built once
(`apps/web/src/components/ui/` or `components/record/`), no per-page variants (§2). They **reuse**
existing primitives heavily:

- **`<NavFab>`** — the raised center action button for `<BottomNav>` (circle, `--accent`, `+` glyph in
  `--button-text`, one shadow token, `--bg` ring, ≥56px, lifted ~16px, `impactOccurred('medium')` on
  press, `press-95`). NOT a `NavLink` — an `onClick` that opens the record sheet. One FAB style only.
- **`<RecordSheet>`** — the record flow controller: composes the existing **`<BottomSheet>`** and swaps
  its body between **`<RecordPicker>`** (Phase A) and **`<SetLogger>`** (Phase B). Owns the
  chosen-exercise state, the session-logged-sets state, and the cross-screen invalidation on close.
- **`<RecordPicker>`** (Phase A, v2 — GYM-72) — built from existing parts: the **Continue tile** (the
  last exercise trained today, a `<Card>`-style tile), a **faint fading divider** below it
  (`.record-divider-faint`), the muscle/exercise **tiles** (the same ≥52px rounded-lg
  `--secondary-bg`/hairline tile, top ~6 + "Show all"), and the **add-inline** field. No 8-item recent
  fast lane. Loading = skeleton tiles. No new card style.
- **`<SetLogger>`** (Phase B) — the set panel: exercise identity (Bebas + `<Chip>`), the "Today" recap
  (reuse `<SetRow>` figures), two **`<Stepper>`s** (reused verbatim from §11.5, just different
  `step`/`min`/`inputMode` props), the **in-sheet sticky SAVE** (the shared `<SheetSaveButton>`,
  §11.4), the PR chip (`PR {w}kg × {r}` from `log-context.pr`, `--accent` text), and the
  "Switch exercise"/"Done" affordances. One `log-context` read powers it; auto-advance + PR-beat live
  here.
- **(maybe) `<SheetSaveButton>`** — if the §11.4 set-editor's sticky Save isn't already a reusable
  component, extract it so the editor and the logger share one sticky-Save (one style only). If it's
  inline today, factor it once here.
- **`<ProfileStub>`** — trivial: an `<EmptyState>` "PROFILE / Coming soon", zero queries. Lives at
  `/profile`. (Designed as a slot, per §12.1.)

No new library is introduced (§1): all of the above are compositions of existing primitives + tokens.

### 12.5 Data, queries, and the cross-screen contract
- **Reads (all via TanStack Query, fired only when the sheet opens — never on app mount):**
  - Continue tile: `["training","day",today]` (reuse the §11 `useTrainingDay` hook) — the last exercise
    trained today is the group whose set has the highest `training_id` (derived client-side).
  - browse: reuse §10.3 hooks `useTopMuscles` / `useTopExercises` / `useMuscles` as-is (muscle/exercise
    tiles).
  - per-exercise on entering Phase B: **one** `["analytics","log-context",muscle,exercise,today]`
    (auto set # + last-session pre-fill + PR), cached with a long `staleTime`/`gcTime` (~10m) so a
    re-entered exercise is instant, disabled until an exercise is chosen (empty path fires nothing,
    §0/ARCH §2).
- **Prefetch (perf, §12.3 #3):** on sheet open, warm `["analytics","top-muscles"]` + `["training",
  "day",today]` and the Continue exercise's `["analytics","log-context",…]`; on muscle pick, prefetch
  that muscle's `["analytics","top-exercises",muscle,200]`. All with the long staleTime/gcTime so the
  session stays instant after the first warm.
- **Write:** `POST /training` mutation. On success: update local "Today" recap + session pre-fill +
  PR anchor (above). **No optimistic cross-screen patch needed** (we're appending, and the sheet shows
  its own recap) — instead, **invalidate on each save settle** so the rest of the app re-fetches:
  `["analytics","summary"]`, `["analytics","activity"]`,
  `["analytics","log-context",muscle,exercise]` (auto set #/PR/recap stay correct),
  `["analytics","exercise-progress",muscle,exercise]`, `["training","days"]` (all windows), and
  `["training","day",today]` (also refreshes the Continue tile). **Why:** a new set changes the
  streak/sets/PR (Dashboard), the activity grid cell, the progress chart, and today's History day —
  missing one = a stale tab (the §11.7 cross-screen-staleness lesson).
- **`createTraining`/`createMuscle`/`createExercise` errors:** the required §4/CLAUDE.md DB-op pattern —
  on a failed `POST /training`, keep the sheet open, re-enable Save, surface a non-scary inline
  message ("Couldn't save that set — try again."), do **not** advance the set number or append the
  recap row (so the optimistic recap never lies). Add-inline failures keep the typed name in the field.

### 12.6 States (empty / loading / error / light+dark / reduced-motion)
- **Loading:** Phase A Continue tile + muscle/exercise tiles render skeleton tiles of the same height;
  entering Phase B shows the steppers immediately with a tiny inline "loading your numbers…"
  placeholder until `log-context` resolves (then the pre-fill fills) — never a blocking spinner, no
  layout shift (§10.4).
- **Empty — brand-new user (no muscles/exercises/history):** Phase A shows an `<EmptyState>`-style
  prompt inside the sheet — Bebas "ADD YOUR FIRST EXERCISE", Sora subline, with the **add-inline**
  field front-and-center (muscle then exercise). After they add one, they drop straight into Phase B
  with empty steppers (no PR yet). The empty path fires no analytics fan-out (top-muscles returns `[]`
  → we skip the top-exercises calls). New-user first-run must never be a blank sheet (§0/ARCH §2).
- **Empty — exercise with no history:** Phase B steppers are empty with `--hint` placeholders, no PR
  chip, Save disabled until valid. First save becomes the PR (celebration fires).
- **Error:** read errors (fast lane/browse) → inline `<ErrorState>` + retry inside the sheet (browse
  still usable if only the fast-lane merge failed — degrade, don't block). Write error → §12.5 inline
  message, sheet stays open.
- **Light + dark:** all surfaces are Telegram `themeParams`; only `--accent`/`--accent-weak` are
  app-owned and already adapt. **Verify in dark:** the `<NavFab>` `--accent` circle + its `--bg` ring +
  shadow against a near-black bar (it must still read as raised, not vanish); the PR chip `--accent`
  text contrast; the sheet scrim over near-black `--bg`.
- **Reduced-motion (`prefers-reduced-motion: reduce`):** no sheet slide (instant), no auto-advance
  recap slide (instant insert), no PR flare (chip value just updates), no FAB press-scale beyond
  instant. **Haptics stay** (medium on open, success on save, the PR success): they are feedback, not
  motion (§9.4).

### 12.7 API: existing vs additions
- **Exists today — the MVP is fully buildable on these (no new endpoint required to ship):**
  `POST /training`, `GET /analytics/top-muscles`, `GET /analytics/top-exercises`,
  `GET /analytics/completed-sets`, `GET /analytics/personal-record`, `GET /analytics/max-reps`,
  `GET /muscles`, `GET /muscles/{id}/exercises`, `POST /muscles`, `POST /exercises`. All RLS-scoped.
- **Nice-to-have additions (separate task — they make it *buttery*, not *possible*):**
  1. **`GET /analytics/recent-exercises?limit`** → ordered list of the user's **last-trained**
     exercises across all muscles, each `{muscle_name, exercise_name, last_weight, last_reps,
     last_date}`. **Payoff:** (a) replaces the §12.2 `top-muscles`+`top-exercises` fan-out with **one**
     ordered read for the fast lane, AND (b) gives **true recency** (last-trained, not just frequent),
     AND (c) carries **last weight/reps** so the cold-open pre-fill is the *actual last working set*
     (strictly better than the PR anchor). This single endpoint is the biggest smoothness upgrade.
  2. **`GET /analytics/last-set?muscle&exercise`** → `{set, weight, reps, date} | null`, the most recent
     set for one exercise. **Payoff:** exact cold-open pre-fill for an exercise reached via *browse*
     (not in the recent list) without loading its full progress series. (Subsumed by #1 for the fast
     lane; useful for the browse path.) Until either lands, the MVP uses `personal-record` for the cold
     pre-fill and same-session state for the hot pre-fill — good, just not the literal last set.
  Both are small, read-only, RLS-scoped analytics endpoints mirroring the existing `top-*` shape;
  neither blocks GYM-64. Flag them as a follow-up so the build can ship on the existing surface first.

### 12.8 Gaps / risks (plugin lens — concrete)
- **Tap-count budget is the acceptance test:** if the hot path (frequent exercise → save → save …)
  isn't ~1 tap/extra-set, the feature failed its purpose. Guard it: pre-fill MUST be filled before the
  user looks (same-session state needs no network; cold open shows steppers instantly and fills when
  `personal-record` resolves), and Save MUST NOT close/reset the sheet. Measure against §12.3's table.
- **Pre-fill correctness (silent-wrong is worse than empty):** a *wrong* pre-filled weight that the
  user saves without noticing corrupts their log. Mitigations: the value is always **visible and
  editable** (big Bebas in the stepper, not hidden); same-session pre-fill (the dominant case) is
  exact; the cold-open PR anchor is clearly the PR (the `PR {w}kg` chip labels it), so the user knows
  to nudge down to today's working weight. The `recent-exercises`/`last-set` additions (§12.7) remove
  this risk by pre-filling the literal last set — until then, the PR anchor is a *known, labelled*
  approximation, not a guess.
- **Set-number race / correctness:** computing `nextSet` from `completed-sets ∪ session sets` (not a
  naive counter) keeps it right even if the user logged a set in the bot earlier today, edited history
  (§11), or has a gap. Recompute after each save and after a Phase-A switch. Two devices logging the
  same exercise the same minute could collide on a set number — acceptable for v1 (single-user, single-
  session is the norm); the server assigns the record id regardless, and a duplicate set number is a
  cosmetic recap issue, not data loss. (A server-side "next set" would fully remove it — out of scope.)
- **Fat-finger on the raised FAB vs tabs:** the lifted center button sits between History-side and
  Progress-side tabs; its ≥56px circle must not overlap the adjacent tabs' ≥44px hit areas. Reserve a
  fixed center slot wide enough that the circle + its ring clear the neighbours; keep ≥8px gap. The
  FAB opens a sheet (reversible) — a mis-tap is cheap (scrim-dismiss), unlike a destructive action.
- **Safe-area with the raised FAB:** the FAB lifts **upward** into content space, never downward, so
  it never collides with the home-indicator/Telegram bottom inset (the bar already pads
  `max(env(safe-area-inset-bottom), --tg-safe-bottom)`, §4). But the lifted circle now overlaps the
  bottom ~16px of scrollable content — so the `<Container>` bottom padding must account for the FAB's
  lift height **in addition** to the nav height (§4: bottom padding = `max(insets) + nav height` →
  becomes `+ nav height + fab lift`), or a card's tap target can hide under the circle. Verify nothing
  interactive sits under the FAB at the content bottom.
- **Add-inline duplicates / typos:** `POST /muscles`/`POST /exercises` are idempotent-ish (return the
  existing or created row per contract), so a duplicate name won't create a clone — but a typo creates
  a private junk exercise. v1 accepts this (matches the bot); trim/normalize whitespace and case-fold
  for the optimistic insert match. No rename/delete-exercise UI in v1 (YAGNI; the bot/admin can clean).
- **"Today" recap honesty:** `completed-sets` returns set *numbers* only (no weight/reps), so for sets
  the server already had before this session the recap shows `Set n ✓` (number only), while this-
  session sets show full `w×r`. This is honest (no fabricated numbers) and still removes the bot's
  set-pick step. The `recent-exercises`/full-day read could enrich it later; not required for MVP.
- **Cross-screen staleness after logging:** the §12.5 invalidation set (summary, activity,
  completed-sets, personal-record, exercise-progress, days, today's day) is mandatory on save-settle /
  sheet-close so Dashboard/Progress/History never show stale numbers — a new set moves the streak, the
  grid cell, the chart, and a PR. Missing one key = a visible inconsistency between tabs (§11.7).
- **BackButton ownership (extends §11.7):** with the record sheet open, the Telegram `BackButton`
  closes the **sheet** first (the `<BottomSheet>` already owns this). Inside the sheet, Phase B's "←
  Switch exercise" is an *in-body* control, not the Telegram Back — so Back from Phase B closes the
  whole sheet (one predictable back-step), it does not step B→A. Wire deterministically; don't strand.
- **`--accent` is "orange enough":** the operator asked for an "orange" FAB; Chalk & Iron's `--accent`
  is the warm orange-red `#E5482F`/`#FF6A4D` (§9.3). We deliberately do NOT introduce a second hue
  (§9.3 "one accent, period") — the FAB IS the brand accent, which reads as a confident
  orange-red and is exactly the "one memorable accent moment" the aesthetic is built around. If the
  operator wants a literally pure-orange FAB, that's a one-token `--accent`-vs-new-`--fab` decision to
  raise at review — flagged, not silently chosen.

### 12.9 Operator decisions (2026-06-05) — locked for the build
1. **FAB color = `--accent`** (the brand Chalk-Red orange, §9.3 one-accent). No new `--fab` hue.
2. **`recent-exercises` is IN scope** for this feature (not deferred): the fast lane uses ONE
   `GET /analytics/recent-exercises` read (last-trained, cross-muscle, with `last_weight`/`last_reps`),
   and the **cold-open pre-fill uses the actual last working set** from it (PR is only the labelled
   fallback when an exercise has no recent row). This is the buttery path. Contract + API = GYM-66/67.
3. **Exercise picker = frequency-first, mirror the bot's "top-N + show all":**
   - Fast lane (cross-muscle): `recent-exercises` chips — 1 tap.
   - Browse by muscle (fallback): the muscle's exercises **frequency-sorted**, render the **top ~6 + a
     "Show all" chip** that expands the rest **client-side** (one `top-exercises?muscle&limit=200`
     fetch; no extra endpoint). Same idea as the bot's "5 + load all", smoother (no round-trip).
