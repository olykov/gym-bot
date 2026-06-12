---
schema_version: 1
id: GYM-131
title: "Save-set choreography: row entrance, button success morph, SET N tick, restrained PR banner"
slug: gym-131-save-choreography
status: review
priority: high
type: feature
labels: [frontend, record, motion, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:20:00Z
start_date: 2026-06-12T17:15:00Z
finish_date: null
updated: 2026-06-12T17:40:00Z
epic: progression
depends_on: []
blocks: []
related: [GYM-130]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md", "docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-131 — Save choreography

## Problem
Concept doc 03 §2 / review doc 01 §2 (operator's reported pain): saving a set is visually
mute — a row appears, the button label flips, nothing registers the event.

## Solution (~700ms total, non-blocking, all behind prefers-reduced-motion)
1. 0ms — success haptic (exists).
2. 0–240ms — new recap row: fade + rise 8px + one background flash (pr-flare language, but
   for EVERY save, softer than the PR flare).
3. 0–180ms — delta badge slides in (translateX 4px + fade) — pairs with GYM-130; degrade
   gracefully if 130 not yet merged (no badge, rest of choreography stands).
4. 200–800ms — Save button success morph: content swaps to "✓ SET 2 — 102.5×8", scale
   1.0→1.02→1.0, then morphs to "SAVE SET 3". No layout shift; input stays interactive.
5. SET N heading: digit roll (translateY swap, 180ms).
6. PR-beat upgrade (operator decision #5 — try it): on weight-PR beat, a full-width in-sheet
   banner "NEW PR · 102.5KG" (Bebas, accent, slide-down 240ms, auto-fade ~1.2s). Existing
   pulse/flare stay. No confetti, no library.
- Reduced-motion: instant updates, haptics remain; banner = static chip flip (current
  behavior).
- Timing/easing via tokens (`--ease-out-soft`, `--dur-reveal`); add a `--dur-save-morph`
  token rather than inline ms.
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin; update spec §12.3
  motion contract.

## Acceptance criteria
- [x] Saving a set produces the doc 03 §2 sequence; rapid double-save (~1 tap/s) never
      queues janky overlapping animations (interrupt cleanly).
      (Implemented: timers cleared + nonce-keyed remounts restart every animation;
      feel-at-1-tap/s on a real device → pending check.)
- [x] PR banner appears only on weight-PR beat; reduced-motion path verified.
      (Banner renders only on `beatPR`; reduced-motion = instant show, timer removal —
      code-verified via the index.css reduce block; device verification pending.)
- [x] Tap-count budget unchanged (~1 tap/set; animation never blocks Save).
      (Save button stays enabled/interactive during the morph; no new taps added.)

## Comments

### 2026-06-12T10:20:00Z — task created
Operator decision #5: banner approved as an experiment — review feel on device before
keeping.

### 2026-06-12T17:40:00Z — implemented (agent wave 6b)

**Files.**
- `apps/web/src/styles/tokens.css` — new motion tokens: `--dur-quick` (180ms — delta
  slide-in, digit roll), `--dur-save-morph` (600ms), `--dur-pr-banner` (1440ms = slide
  240 + hold to 1.2s + fade 240); sync constants noted in comments.
- `apps/web/src/index.css` — GYM-131 block: `row-flash` keyframe (accent @12% — softer
  than the PR-only 22% pr-flare) + `.row-enter` (reuses `reveal-rise` for fade+rise 8px)
  + the combined `.row-enter.pr-flare` rule (PR rows keep the rise, upgrade the flash);
  `delta-slide` (`.delta-enter`, translateX 4px + fade, `animation-delay: var(--dur-reveal)`
  — fires after the row lands, pure CSS); `save-morph-scale` (1.0→1.02→1.0);
  digit-roll (`.roll-clip/.roll-out/.roll-in`); `pr-banner` lifecycle keyframes.
  Reduced-motion block extended: all five animation families off, `.delta-enter`
  forced back to opacity 1 (its base hides it for the CSS delay), `.roll-out` hidden
  (its animationend can never fire).
- `apps/web/src/components/record/useSaveChoreography.ts` — NEW hook: one owner for
  morph/pulse/flareSet/banner + their timers. Every `onSave` clears pending timers and
  restarts with a fresh nonce (the render key that remounts animated elements) →
  rapid double-save interrupts cleanly; unmount clears all. Exports the named ms
  constants (`SAVE_MORPH_MS`, `PR_PULSE_MS`, `PR_BANNER_TOTAL_MS`).
- `apps/web/src/components/ui/RollingNumber.tsx` — NEW reusable digit roll: prop-derived
  prev-value state, old digit slides up/out (absolute), new slides up/in, animationend
  clears; inherits the surrounding font (Bebas in the SET heading).
- `apps/web/src/components/ui/SheetSaveButton.tsx` — optional `success` payload prop
  ({label, nonce}): check glyph (inline SVG, not emoji) + "Saved set n — w×r" content,
  scale on the inner span only (fixed min-h → zero layout shift), button interactive
  throughout. SetEditor call sites unaffected (prop optional).
- `apps/web/src/components/record/PrBannerOverlay.tsx` — NEW: the in-sheet banner
  (chip-banner per §9.3: `--accent-weak` bg + `--accent` Bebas text + hairline — accent
  never fills a surface), aria-live polite wrapper always mounted, nonce-keyed restart.
- `apps/web/src/components/record/ComparisonRecap.tsx` — `justSavedSet` prop: that row
  gets `.row-enter` (both recap modes) and its delta badge the `.delta-enter` wrapper;
  PR rows combine `.row-enter.pr-flare`.
- `apps/web/src/components/record/SetLogger.tsx` — choreography state moved into the
  hook (replaces the inline pulse/flare useState+setTimeout); SET heading rolls only
  the digit (catalog template split around `{n}` → words stay i18n'd); passes
  `justSavedSet` + `success` morph content; root now `relative` for the banner overlay.
- `apps/web/src/i18n/messages.ts` — `logger.savedSet` (en/ru, compact «Записан сет…»),
  `logger.prBanner` (en/ru).

**Decisions.**
- Morph implemented as a hook-owned payload (`success` prop), not SheetSaveButton state —
  the shared button stays presentational; SetEditor untouched.
- PR banner lifecycle = ONE CSS animation (slide/hold/fade percentages of
  `--dur-pr-banner`) + one removal timer of the same total → reduced motion gets
  "instantly shown, still removed on time" for free (banner is information, so it
  still shows — per spec).
- `beat` logic (GYM-104 derived effectivePR) unchanged; existing pr-pulse/pr-flare stay,
  flash-on-every-save is the new, softer `row-flash`.
- Heading digit split uses the raw catalog template (`MESSAGES[key][locale].split("{n}")`)
  so locales with different word order keep working.

**Verification.** Bench (rsync → /tmp/bench): `tsc --noEmit` ✓, `npm run lint`
(--max-warnings 0) ✓, `vitest run` ✓ **136 tests** (was 127, +9 — see GYM-132 derive
suites), `npm run build` ✓. File sizes kept <500 (SetLogger 498 after extracting
PrBannerOverlay). Pending: real-device feel pass (morph rhythm at 1 tap/s, banner
duration, reduced-motion on iOS).

**Overlap note.** `SetLogger.tsx` and `messages.ts` carry hunks of BOTH GYM-131 and
GYM-132 (built in one wave; SetLogger's `onSetLogged` prop requires RecordSheet from
GYM-132 to compile). Commit order: GYM-131 first (tokens/index.css, useSaveChoreography,
RollingNumber, PrBannerOverlay, SheetSaveButton, ComparisonRecap), then GYM-132
immediately after (RecordSheet, SessionSummaryPanel, derive, tests) — with SetLogger.tsx
+ messages.ts included in the GYM-132 commit so every commit compiles; or one combined
commit referencing both tasks.

**Suggested commit:** `Add save choreography with success morph and PR banner`
