---
schema_version: 1
id: GYM-128
title: "apps/web upgrade pack: Tailwind 4 (CSS-first tokens) + Vite latest + react-router 7"
slug: gym-128-web-upgrade-pack
status: review
priority: medium
type: chore
labels: [frontend, deps, build]
assignee: agent
model: claude-fable-5
reporter: oleksii
created: 2026-06-12T10:00:00Z
start_date: 2026-06-12T19:10:00Z
finish_date: null
updated: 2026-06-12T19:40:00Z
epic: tech-debt
depends_on: [GYM-124]
blocks: []
related: [GYM-121, GYM-129]
commits: []
tests: []
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-128 — Upgrade pack (Tailwind 4 / Vite / router 7)

## Problem
Review doc 02 §2. Stack is one-two majors behind. Best ROI: Tailwind 4's CSS-first
`@theme` — our tokens already live in `tokens.css`, so `tailwind.config.js` collapses into
CSS and the token system becomes single-source.

## Solution
- **Tailwind 3 → 4**: migrate config to `@theme` in tokens.css; verify every custom token
  class (`bg-bg`, `text-hint`, `h-nav`, `max-w-container`, `text-stat`…) compiles
  identically; visual smoke light+dark.
- **Vite 5 → latest major** (check current; 5→6→7 path): config is tiny, low risk; bump
  Node in CI if required.
- **react-router-dom 6 → 7**: run the codemod; verify BrowserRouter/data-router behavior;
  unlocks built-in `viewTransition` for GYM-121.
- **React 19 explicitly OUT of scope** — separate decision later (repo docs still say 18;
  update docs first).
- Order: each upgrade = its own commit, deployable independently; abort any step whose
  fallout exceeds a day.

## Acceptance criteria
- [x] Build + lint + tests green; bundle size not regressed (compare `vite build` output).
  (Main JS +22 kB from router 7; chart chunk −540 kB from GYM-129 — total JS −35%.)
- [ ] Manual smoke: record flow, history edit, progress chart, both themes, 360px.
  (Operator step — agent verified emitted CSS class-by-class, see comment.)
- [x] tailwind.config.js removed or reduced to content-scan only.
  (Reduced to an unused `export default {}` stub — agent sandbox cannot delete files;
  safe to `git rm` together with this change.)

## Comments

### 2026-06-12T10:00:00Z — task created

### 2026-06-12T19:40:00Z — implemented (agent wave 8)

Done in strict stages, full gate (`tsc --noEmit` + `eslint --max-warnings 0` +
`vitest run` 185/185 + `tsc && vite build`) green after EVERY stage. No stage aborted.

**Bundle sizes (vite build):**

| asset | before (wave start) | after | note |
|---|---|---|---|
| main `index-*.js` | 428.15 kB (gzip 127.93) | 450.01 kB (gzip 132.32) | +react-router 7 |
| `ExerciseProgressChart-*.js` | 1,056.75 kB (gzip 351.61) | 516.38 kB (gzip 174.52) | GYM-129 |
| `index-*.css` | 24.58 kB (gzip 6.23) | 31.86 kB (gzip 7.27) | TW4 emits theme vars/@property plumbing |
| build time | ~5.9s | ~0.45s | Vite 8 (Rolldown) |

**Stage 2 — Vite 5.4.21 → 8.0.16** (+ `@vitejs/plugin-react` 4 → 6.0.2): zero config
fallout — existing `vite.config.ts` (alias/proxy/allowedHosts) valid as-is. vitest 4.1.8
already supports vite ^8 (peer-checked). CI `web-checks` uses node 22 ≥ 22.12 — adequate,
no workflow change needed. Commit: `Upgrade vite to 8 with plugin-react 6`

**Stage 3 — react-router-dom 6.20 → 7.17**: drop-in; every API we use
(`createBrowserRouter`/`RouterProvider`/`Navigate`/`NavLink`/`Outlet`/`useParams`/
`useLocation`/`useNavigationType`/`useNavigate`) is stable in v7, imports stay
`react-router-dom`. Decision: built-in `viewTransition` NOT adopted — our
`useTransitionNavigate` sets directional `data-nav-transition="push|pop"` on `<html>`
(GYM-121 slide direction), which the router flag cannot do; not zero-risk, kept ours.
Main chunk +28 kB raw (router 7 is bigger) — accepted. Commit:
`Upgrade react-router-dom to 7`

**Stage 4 — Tailwind 3.3 → 4.3 (CSS-first)**:
- `@import "tailwindcss"` replaces the three `@tailwind` directives; build through
  `@tailwindcss/vite` (recommended v4 path); `postcss.config.js` → explicit no-op
  (autoprefixer + postcss devDeps dropped — v4 prefixes via Lightning CSS);
  `tailwind.config.js` → unused stub (v4 auto-detects content; dist/ is gitignored so
  it is not scanned).
- Theme moved to `tokens.css`: restricted spacing scale recreated EXACTLY
  (`--spacing: initial` kills v4's dynamic numeric scale, then explicit
  `--spacing-0/1/2/3/4/6/8` = 0/4/8/12/16/24/32px + header/nav/tile as
  `@theme inline` var refs) — off-scale utilities (`p-5`, `h-44`, `gap-1.5`,
  `w-16`…) stay non-emitting exactly as under the v3 replaced-spacing config;
  font sizes incl. the `text-base` 0.9375rem OVERRIDE + micro/label/stat/stat-lg/title
  with line-height/letter-spacing companions; colors as `@theme inline` var() maps;
  `max-w-container/chip/chip-wide` via the v4 `--container-*` namespace;
  radius/fonts/ease moved INTO `@theme` as literals (same names/values — avoids
  same-name self-reference); `shadow-card` + `z-chrome/z-sheet/z-sheet-nested` as
  `@utility` (no v4 namespace for z-index; shadow stays a runtime var because dark
  mode overrides it).
- Verified by diffing the FULL class-selector set of the built CSS v3 vs v4: every
  utility identical (`.p-4{padding:16px}`-equivalent via vars, `.h-tile`,
  `.max-w-container`, `.text-stat`, `.z-chrome`, `.rounded-*` radius tokens,
  `.divide-hairline`, `motion-reduce:*`, `min-h-[44px]`, all 17 custom @keyframes,
  the prefers-reduced-motion block). Differences, all explained:
  1. `max-w-[8rem]` gone — appeared ONLY in a Chip.tsx comment (TW3 scanned comments).
  2. `h-px` NOW EMITS (static 1px in v4): it was a dead class under the v3 replaced
     spacing scale, so 5 authored hairline dividers (ManageSheet/ManageMoveView/
     MusclePanel) silently had height 0 — they now render as designed. Intended fix,
     flag at visual smoke.
  3. Two bare `rounded` usages rewritten to `rounded-md` (identical 12px — v3 DEFAULT
     = md; bare `rounded` has no such mapping in v4).
  4. Preflight parity shim added in `@layer base`: v4 sets `cursor: default` on
     buttons, v3 used `pointer` — restored.
  5. `outline-none` (5 inputs) kept: v4 semantics (`outline-style: none`) visually
     identical to v3's invisible-outline for these fields, all have explicit focus
     styles.
- Known dead classes (pre-existing, unchanged): `h-5 w-5`, `w-12/16/20/28/32/40`,
  `gap-1.5`, `mt-0.5`, `mb-5`, `mt-5` are off the restricted scale and emit nothing
  (now as before) — follow-up cleanup candidate.
- Docs: `docs/frontend-spec.md` §1 and repo CLAUDE.md name no versions — no edits.
Commit: `Migrate Tailwind to 4 with CSS-first theme`

**Stage 5 — final**: fresh rsync of the real repo into a clean bench, `npm ci`, full
gate green (tsc / lint / 185 tests / build). CI `web-checks` job unchanged and valid
(`npm ci` + same scripts; node 22).

React 18 untouched (out of scope per task). Operator follow-ups: manual visual smoke
(both themes, 360px), `git rm tailwind.config.js` + `postcss.config.js` if the no-op
stubs are unwanted.
