---
schema_version: 1
id: GYM-125
title: "apps/web correctness: 401 re-auth, 409 set-collision message, SetRow pointer capture, focus trap claim"
slug: gym-125-web-correctness-fixes
status: review
priority: high
type: bug-fix
labels: [frontend, bug, auth, record]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:45:00Z
start_date: 2026-06-12T13:30:00Z
finish_date: null
updated: 2026-06-12T13:30:00Z
epic: tech-debt
depends_on: [GYM-124]
blocks: []
related: [GYM-119]
commits: []
tests: []
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-125 — Correctness fixes (review doc 02 §5)

## Problem
Four independent correctness gaps found in the 2026-06 tech review.

## Solution
1. **401 handling**: a JWT surviving in sessionStorage past expiry currently yields endless
   ErrorStates. In `apiRequest` (or a QueryCache `onError`), on 401: `clearSessionToken()`
   → one re-run of `authenticateWithInitData(getInitData())` → retry the request once;
   on second 401 surface the auth ErrorState.
2. **409 on `POST /training`** (set-number collision, spec §12.8): SetLogger shows generic
   "Couldn't save…". Distinguish by `ApiError.status === 409` → "Set N already exists —
   refreshed your numbers." + invalidate that exercise's log-context so `nextSet` recomputes.
3. **SetRow swipe**: add `e.currentTarget.setPointerCapture(e.pointerId)` on pointerdown —
   a finger leaving the row currently strands the swipe half-open.
4. **BottomSheet focus trap**: JSDoc claims focus-trap; only initial focus exists. Either
   implement a minimal trap (Tab cycling within the panel) or fix the docstring. Decide at
   impl (trap preferred — cheap, desktop benefit).

## Acceptance criteria
- [ ] Expired-token session self-heals without user-visible error (verified by forcing a
      stale token).
- [x] 409 path shows the specific message and auto-corrects the set number.
- [x] Swipe never strands when the pointer leaves the row; unit/RTL tests where practical.

## Comments

### 2026-06-12T09:45:00Z — task created

### 2026-06-12T13:30:00Z — implemented (agent wave 2)

Files changed (this task's commit):
- `apps/web/src/api/reauth.ts` (new) — single-flight `reauthenticate()`: clears the stale
  token, re-runs `authenticateWithInitData(getInitData())` once; concurrent 401s share one
  in-flight promise. Returns `false` (no retry) when initData is absent (outside Telegram)
  or the exchange itself fails.
- `apps/web/src/api/client.ts` — `apiRequest` delegates to a private `performRequest` with
  an `isRetry` guard; on a 401 from an authed, non-retried request it re-auths once and
  retries once; second 401 throws as before. `reauth` is imported dynamically on the 401
  path only — no static import cycle (reauth → auth → client), test-env safe.
- `apps/web/src/components/record/derive.ts` — new pure `saveErrorMessage(error, attemptedSet)`:
  `ApiError.status === 409` → "Set {n} already exists — refreshed your numbers."; anything
  else keeps the generic message.
- `apps/web/src/components/record/SetLogger.tsx` — error line now renders
  `saveErrorMessage(create.error, create.variables?.set ?? nextSet)`. The set-number
  auto-correct rides on `useCreateTraining`'s `onSettled` log-context invalidation (fires
  on error too → `completed_sets` refetch → `computeNextSet` recomputes).
- `apps/web/src/hooks/useRecord.ts` — JSDoc guard: the invalidation must stay in
  `onSettled` (not `onSuccess`) or the 409 auto-correct breaks.
- `apps/web/src/components/ui/SetRow.tsx` — `setPointerCapture(e.pointerId)` on pointerdown,
  feature-checked + try/catch for older WebViews; move/up keep streaming to the row when
  the finger drifts out, so the swipe never strands half-open.
- `apps/web/src/components/ui/BottomSheet.tsx` — real minimal focus trap: Tab/Shift+Tab
  cycle within the open panel (focusables queried at keydown time); JSDoc updated to match.
  Scrim button is outside the panel and intentionally excluded (aria-modal).
- `apps/web/src/components/record/derive.test.ts` — 3 new tests for `saveErrorMessage`
  (409 with set number, other statuses, non-ApiError values).

Behavior notes:
- 401 self-heal is silent: the failed query resolves with the retried response; only a
  second consecutive 401 surfaces the auth ErrorState (unchanged path).
- Criterion 1 left unticked: the code path is unit-typed and reviewed, but the live
  "force a stale token" verification on a real session remains for the operator.
- SetRow swipe and the focus trap are DOM/pointer-heavy; covered by manual smoke, not RTL
  (no DOM test environment configured in the GYM-124 vitest setup — node env).

Verification: bench run (`/tmp/bench/apps/web`) — `tsc --noEmit` clean, `eslint --max-warnings 0`
clean, `vitest run` 58/58 passed (5 files), `vite build` OK.

Suggested commit (GYM-125 files above):
`Self-heal 401, 409 set message, pointer capture, focus trap`
