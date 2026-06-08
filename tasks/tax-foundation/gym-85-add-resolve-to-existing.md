---
schema_version: 1
id: GYM-85
title: "Add resolves-to-existing (silent unhide) + dedup on create & rename within visible set"
slug: gym-85-add-resolve-to-existing
status: done
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T13:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T14:00:00Z
epic: tax-foundation
depends_on: [GYM-84]
blocks: []
related: [GYM-86]
commits: [013d658, 75bb30b, f0d84ee]
tests: [apps/api/tests/test_gym85_resolve_dedup.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-85 — Resolve-to-existing + dedup

## Problem
Adding/renaming should be smart about existing names (incl. hidden ones), per ADR 0001.

## Scope (layers): contract + API + frontend (split into waves at execution)
- API add flow: normalize → look up by name_key in the caller's VISIBLE set →
  - match found & visible → return it (no dup);
  - match found but HIDDEN → **silently unhide** and return it (no prompt — operator decision);
  - no match → create the custom as today.
- Dedup-on-create: typing a name whose key matches one you ALREADY have visible → 409 "you already have
  this exercise/muscle".
- Dedup-on-rename: renaming (own custom OR a canonical alias) to a key that collides with another item in
  your visible set → 409, same message.
- Frontend: surface the unhide-and-select silently; show a graceful inline dedup message on the explicit
  collision cases.

## Key decisions (operator)
- Same-name-as-a-hidden-item → unhide silently, do not ask.
- Different-string with no alias link (e.g. "жим лёжа" while Bench Press hidden) → just create the custom;
  do nothing clever (matching is a later phase).

## Acceptance
- [x] Re-adding a hidden item unhides it silently; adding/renaming to an existing visible name → 409 with a
      clear message; a genuinely new name still creates; covered by tests; build/suite green.

## Comments

### 2026-06-08 — Contract slice (commit 013d658)

Done in `packages/api-contract/openapi.yaml` only (CONTRACT slice; API/frontend follow).

- Added optional `resolution` to both `Muscle` and `Exercise` read schemas — string enum
  `[created, unhidden, existing]`, `type: ['string', 'null']`, NOT required (modeled like
  `is_mine`). Stays absent/null on list/read responses → non-breaking for bot/admin clients.
  Desc: 'created' = new row; 'unhidden' = an existing hidden item was silently unhidden;
  'existing' = item already existed and visible (no duplicate created).
- Documented find-or-create-or-unhide on `POST /muscles` and `POST /exercises` (user by-name):
  name normalized to key; if a row with that key exists in the caller's scope → hidden is
  silently unhidden (resolution=unhidden, HTTP 200), visible is returned as-is with no duplicate
  (resolution=existing, HTTP 200); otherwise a new row is created (resolution=created, HTTP 201).
  Both endpoints now document the 200 (resolved) and 201 (created) responses. Request bodies
  unchanged.
- Rename PATCH contract untouched (409-on-duplicate already exists; GYM-85 rename dedup is an
  API-internal key-based comparison, no contract change).
- `make validate` passes (OpenAPI 3.1, 34 paths, 38 schemas). Regenerated both clients
  (`make gen-python`, `make gen-typescript`). Python `models.py` imports cleanly: `Resolution`
  enum = [created, unhidden, existing]; `resolution` present on `Muscle` and `Exercise`.
  TS `tsc --noEmit --strict` passes; `resolution?: "created" | "unhidden" | "existing" | null`
  present on both. Note: TS client is gitignored (regenerated on demand), Python client is the
  installable tracked artifact.

### 2026-06-08 — Frontend slice (commit f0d84ee)

Implemented in `apps/web/src/components/record/` only.

**Per-resolution UX:**

- `created` — unchanged behavior: auto-select item using `data.name` (canonical), proceed.
- `unhidden` — fully silent: auto-select `data.name`, proceed. No message, no prompt.
- `existing` — show non-blocking "You already have 'Name'." hint AND proceed with the
  returned item. The auto-select uses `data.name` in all cases (canonical backend name, not
  the user-typed string).

**Where branching happens:**

- `submitMuscle` (RecordPicker): after `pickMuscle(canonicalName)` returns (which navigates
  to the exercise step and clears local `resolveHint`), sets `resolveHint` if `existing`. The
  hint renders in the exercise panel of RecordPicker (which stays mounted). Cleared on
  back-navigation, new add field open, or goBack.
- `submitExercise` (RecordPicker): since `onPick` immediately transitions to Phase B and
  RecordPicker unmounts, the hint is bubbled to RecordSheet via the new `onCreateHint` callback
  prop. RecordSheet holds `createHint` state and passes it to SetLogger.

**Message treatment:**

- For exercises: dismissible banner in SetLogger (below "← Switch exercise"), Chalk & Iron
  tokens — `--secondary-bg` background, `border-hairline`, `text-label text-hint`. Dismissed by
  × button or on exercise switch or sheet close.
- For muscles: small `text-label text-hint` line in the exercise panel of RecordPicker, below
  the AddInlineField / "+ Exercise" button area.
- Empty-user path: same `resolveHint` renders in the inline field area.

**File changes:**
- `RecordPicker.tsx`: `resolveHint` state, `onCreateHint` prop, `submitMuscle`/`submitExercise`
  branch on resolution, hint clearing on navigation events.
- `RecordSheet.tsx`: `createHint` state, passes `onCreateHint` to RecordPicker and `createHint`
  + `onClearCreateHint` to SetLogger; clears hint on sheet close and on exercise switch.
- `SetLogger.tsx`: `createHint`/`onClearCreateHint` optional props, dismissible hint banner.
- `docs/frontend-spec.md`: §12.11 note added.

**Build result:** `tsc && vite build` — green, 0 type errors. Chunk-size warning is pre-existing.

**Needs live-device pass:**
- Verify hint banner shows at correct position above exercise identity in SetLogger on iOS/Telegram.
- Confirm × dismiss works and doesn't leave stale state on re-enter.
- Confirm `unhidden` muscle/exercise truly shows nothing (no hint, no flash).
- Test the empty-user path hint (muscle "existing" in the inline field area).

### 2026-06-08 — API slice (commit 75bb30b)

Implemented in `apps/api/` only (API slice; frontend follows separately).

**Resolution logic and precedence (POST /muscles, POST /exercises):**

The endpoint first checks for the caller's OWN row (created_by == uid), then a GLOBAL row,
then falls through to create. The DB function `app_name_key(:input)` is called in SQL for
every lookup — normalization never happens in Python, so DB and API can never diverge.

1. Key matches caller's OWN row → return it, `resolution=existing`, HTTP 200.
2. Key matches a GLOBAL row NOT hidden for this user → return it, `resolution=existing`, HTTP 200.
3. Key matches a GLOBAL row that IS hidden → delete UserHiddenMuscle/UserHiddenExercise row
   silently → return the global row, `resolution=unhidden`, HTTP 200.
4. No key match → INSERT new own row, `resolution=created`, HTTP 201.

Own items (created_by != NULL) are never hidden (no UserHidden row for own items); so
hidden-check applies only to globals — the precedence order correctly reflects this.

**How 200 vs 201 is set:** The endpoint declares `Response` as a FastAPI dependency
injection parameter (`http_response: Response`). Each branch sets
`http_response.status_code` explicitly (200 or 201) before returning. The ORM object
(Muscle/Exercise) is returned directly and serialised by the `response_model` as usual.
No JSONResponse wrapping needed.

**Rename key-based dedup (PATCH /muscles/{id}, PATCH /exercises/{id}):**

The old name-equality pre-check (`WHERE name == new_name`) was replaced with a key-based
check: `WHERE name_key = app_name_key(:new_name) AND id <> :self_id`. This catches
separator/case variants ("Bench Press" and "bench-press" are the same key). Renaming to
the item's own current key (e.g. same name, different whitespace) is allowed because
`id <> self_id` excludes the row itself. The IntegrityError backstop on the unique index
is kept as a last-resort safety net; on IntegrityError the session is rolled back before
raising 409.

**Schemas:** `resolution: Optional[str] = None` added to both `Muscle` and `Exercise`
read schemas in `apps/api/app/schemas/schemas.py`. The field stays `null` on list/GET
endpoints (set only by create endpoints), which is non-breaking.

**Test suite:** `apps/api/tests/test_gym85_resolve_dedup.py` — 16 integration tests:
all 4 resolution branches for muscles (own, visible global, hidden global, new) and for
exercises; separator/case variant test for both; rename key-dedup 409 and 200 cases for
both; rename to own current key allowed. Full suite result: **294 passed, 0 failed**.
