---
schema_version: 1
id: GYM-105
title: "apps/web: log-context stale 10min → refetch-on-open + History delete/edit invalidates it (fix stale PR/history/completed-sets)"
slug: gym-105-logcontext-freshness
status: done
priority: critical
type: bug-fix
labels: [tax-fixes, frontend, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T19:30:00Z
start_date: 2026-06-08T19:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T20:00:00Z
epic: tax-fixes
depends_on: [GYM-104]
related: [GYM-72, GYM-99]
commits: [725b406]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-105 — log-context freshness on open

## Problem (live, prod-verified — DATA SAFE)
Prod: Dumbbell row (id 34, Back) = 144 sets, PR 50; NO sets today (the user's History delete DID remove
today's sets in the DB). Yet the SetLogger on reopen still showed: no PR/history pulled, and 2 "completed"
sets with checkmarks that were already deleted.

Root cause: `useLogContext` has `staleTime = SESSION_STALE (10min)` (GYM-72 perf). On reopen within 10min,
React Query serves the CACHED snapshot without refetching → stale completed_sets (deleted sets still show
as ✓), stale/empty PR + last-session. GYM-104 derives PR from this same stale `ctx.data`, so it can't help.
Compounded by: History delete/edit does NOT invalidate the log-context cache. (Telegram Mini App JS caching
may also leave the user on older code — operational, not in scope.)

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; tokens only, no UI redesign)
- Make `useLogContext` ALWAYS fresh on open: set `staleTime: 0` + `refetchOnMount: 'always'` (keep a
  `gcTime` so the cached snapshot renders INSTANTLY as placeholder while the fresh fetch runs — instant feel
  preserved, but server truth always arrives and replaces it). The query is tiny/sargable (GYM-59), so the
  per-open refetch cost is negligible. Verify the SetLogger recap (completed_sets ✓) + PR + last-session
  pre-fill all reflect current server state on every open.
- Make the History set delete/edit/add mutations invalidate the per-exercise log-context (and completed-sets
  / day / progress) so an open SetLogger updates immediately too. Find the History mutation hook(s)
  (HistoryDay / SetEditor / the training delete-edit hook) and add the `["analytics","log-context", muscle,
  exercise]` (prefix) + `["analytics","exercise-progress",...]` invalidations.
- Keep all behavior; no visual redesign. Confirm: log 2 sets → delete them in History → reopen the exercise
  → recap shows NO leftover ✓ and the real PR shows.

## Acceptance criteria
- [ ] On every SetLogger open, completed_sets / PR / last-session reflect current server state (no stale ✓,
      real PR shown); History delete/edit invalidates log-context; build green.

## Comments

### 2026-06-08T19:30:00Z — task created
Prod-verified data safe (Dumbbell row 144 sets/PR 50; today's sets deleted in DB). Bug = 10-min stale
log-context cache served on reopen + History delete not invalidating it. Critical.

### 2026-06-08T20:00:00Z — implemented (commit 725b406)

**useLogContext freshness change (apps/web/src/hooks/useRecord.ts)**
- `staleTime` changed from `SESSION_STALE` (10 min) to `0`.
- `refetchOnMount: 'always'` added so React Query always fires a fresh fetch when
  the SetLogger mounts (i.e. every exercise open), even if the query key is already
  in cache.
- `gcTime` kept at `SESSION_GC` (10 min): the previous cached snapshot stays in
  memory and renders INSTANTLY as a placeholder while the fresh network fetch runs
  in the background. The instant-feel on reopen is preserved; the server truth
  (real completed_sets, real PR) replaces the stale snapshot once the response lands.

**History mutation invalidation (apps/web/src/hooks/useTraining.ts)**
- Added `void qc.invalidateQueries({ queryKey: ["analytics", "log-context"] })` to
  `invalidateAfterMutation`, which is called by both `useEditSet.onSettled` and
  `useDeleteSet.onSettled`.
- This broad prefix invalidation covers every muscle/exercise/date combination so
  any delete or edit in History immediately marks all log-context cache entries as
  stale. On the next SetLogger open (refetchOnMount: always), fresh data is fetched.
- `["analytics", "exercise-progress"]` was already present in `invalidateAfterMutation`.

**End-to-end reasoning**: log 2 sets → delete them in History → reopen that exercise
in the picker → `invalidateAfterMutation` marks the log-context stale → `refetchOnMount:
always` fires a fresh fetch → server returns empty `completed_sets` → recap shows NO
leftover checkmarks; real server PR is shown.

**Build result**: `npm run build` (tsc + vite) passed with no type errors. Pre-existing
chunk-size warning unrelated to this change.

**Needs live-device pass**: confirm on a real device/Telegram Mini App that:
- Reopening an exercise after deleting its sets in History shows no stale ✓ recap rows.
- The PR chip reflects the correct server PR (not a stale or missing value).
- The instant-placeholder render (brief stale data → fresh data) feels acceptable
  on slow connections (no jarring blank flash).
