# ADR 0002 — Canonical layer: per-user rename overrides + linking (GYM-86 / tax-linking)

- Status: proposed (design; awaiting operator review + manual prod migration)
- Date: 2026-06-08
- Extends: ADR 0001 (reference + overrides, not a per-user fork)
- Tasks: GYM-86 (override), GYM-87 (canonical_id + alias schema), GYM-88 (merge), GYM-89 (Link/Unlink)

## Context
ADR 0001 chose **reference + overrides**: one shared canonical catalog; a user "owns" a per-user layer
(custom rows + hide flags + — now — a rename override). Two capabilities remain to design precisely:
- **GYM-86** — a user renames a CANONICAL (global) exercise/muscle to their own name, keeping the link
  (so training history + cross-user features stay on the canonical id; NO history split).
- **tax-linking** — formal `canonical_id` link + alias table, a **merge** op (GYM-88), and a **Link/Unlink**
  flow (GYM-89) to attach a custom exercise to a canonical for cross-user features.

This is the highest-risk change to the name-resolution layer that the tax-fixes wave (GYM-99/104/105) just
stabilized. It must be built behind thorough tests and is **held until the operator reviews this design and
applies the migrations to prod** (migrations are manual — see [[gymbot-taxonomy-and-migrations]]).

## Decision — schema (additive; migrations 0005 + 0006)
- **0005 (GYM-86):** `user_exercise_override(user_id, exercise_id→exercises, display_name,
  display_name_key GENERATED app_name_key(display_name), PK(user_id,exercise_id), idx(user_id,
  display_name_key))` and `user_muscle_override(...)` analogous. RLS: per-user isolation (same posture as
  `user_hidden_*`). Renaming a CANONICAL = upsert an override row; renaming an OWN custom = UPDATE its
  `name` (unchanged from today). Training never moves → no history split.
- **0006 (GYM-87):** `exercises.canonical_id` (nullable self-FK; NULL for canonical rows + unlinked
  customs; set when a custom is Linked) + `exercise_alias(canonical_id→exercises, alias_name, name_key
  GENERATED, lang, UNIQUE(canonical_id,name_key), idx(name_key))` — catalog RLS. No seeding here.

## Decision — name→id resolution (the invasive part: 12 sites, see impact map below)
Today resolution is scattered and partly inconsistent (some sites still match exact `.name`, not name_key).
**Centralize into ONE override-aware resolver** and route every single-exercise/single-muscle name lookup
through it:
```
resolve_exercise_id(db, uid, muscle, exercise) -> id | None:
  key_m = app_name_key(muscle); key_e = app_name_key(exercise)
  1. caller's OWN custom whose name_key == key_e (in the muscle resolved by override-or-name) → its id
  2. caller's OVERRIDE whose display_name_key == key_e → the linked canonical exercise_id
  3. GLOBAL canonical whose name_key == key_e (muscle by name_key) → its id
  else None
resolve_muscle_id(db, uid, muscle) -> own name_key → override display_name_key → global name_key.
```
Priority own → override → global guarantees the user's renamed/own name wins, and the value maps to the
SAME id their history lives on (no split). **Prerequisite cleanup (GYM-86a):** fix the lingering EXACT-name
resolution sites to go through this resolver: `top-exercises` (analytics_router:278 muscle), `POST /exercises`
muscle lookup (exercises_router:167), `POST /training` (bot_router:516/524), legacy `POST /user/training`
(router.py:255/260). (These are a latent variant-name bug independent of overrides.)

### Resolution sites to route through the resolver (LIST A — 12)
analytics: completed-sets (78-79), history (128-129), personal-record (180-181), max-reps (231-232),
top-exercises (278 — exact today), exercise-progress + log-context (via `_resolve_exercise_id` 823-854).
exercises: POST /exercises muscle lookup (167 — exact). bot: POST /muscles (214/232, name_key), POST
/training (516/524 — exact). legacy: POST /user/training (255/260 — exact).

## Decision — effective display name (10 sites, no shared serializer)
A renamed exercise/muscle must show the user's name everywhere it's returned. Two integration points:
- **Lists** → enrich in the visibility services (`visible_muscles`, `visible_exercises_for_muscle`,
  `app/services/visibility.py`): LEFT JOIN the override and set the effective name on the ORM object before
  return. Covers `/muscles`, `/muscles/{id}/exercises`, `/muscles/hidden`, `/exercises/hidden`.
- **Analytics/history SQL** → add a `LEFT JOIN user_*_override` + `COALESCE(override.display_name, x.name)`
  in each name-returning query: `/training/days` (ARRAY_AGG m.name → coalesced), `/training/day/{date}`
  (e.name/m.name aliases), `/analytics/top-muscles`, `/analytics/top-exercises`, `/analytics/recent-exercises`.
- **Shared/cross-user surfaces (future leaderboards, GYM-13/89):** display the **canonical** name, never a
  private alias. The override is per-user display only; aggregation keys on canonical id.

(No shared serializer exists today — this is unavoidably ~10 touch-points. A future refactor could route all
name projection through one helper; out of scope now.)

## Edge-case rules (recommended defaults — flag for operator)
1. **Rename collides with an existing visible name** (own/override/global effective key) → 409, reuse the
   GYM-85 dedup message. (Renaming to the item's own current effective key = no-op/allowed.)
2. **Rename a canonical to a name that equals another global** → allowed (it's only YOUR alias) but the 409
   rule above still blocks if it collides with something in YOUR visible set.
3. **Unrename / reset** → deleting the override row reverts to the canonical name (add an "Reset name"
   affordance, or Unlink-style). 
4. **Hidden + override** independent (a renamed canonical can still be hidden).
5. **Aggregation/leaderboard identity** = `COALESCE(exercises.canonical_id, exercises.id)` so a linked
   custom and the canonical aggregate together; a user's own PR/history stays on their own id (no split).

## tax-linking design
- **GYM-88 merge(A→B)** (admin/maintenance): repoint user overrides, `canonical_id` backpointers, and
  `training` from A→B; move A's aliases to B + add A's name as a redirect alias; deprecate A. Transactional,
  idempotent, audited. Needed because canonical entries WILL turn out to be duplicates over time.
- **GYM-89 Link/Unlink**: set `exercises.canonical_id` on a user's CUSTOM exercise → a canonical in the
  SAME muscle (pick-from-list, no free-add — operator decision). Linked customs are highlighted in the
  picker; Unlink clears `canonical_id`. Powers cross-user features without merging the user's history.
  (UX decisions for operator: where the Link entry point lives; long-tap vs explicit button; how "linked"
  is shown.)

## Migration & rollout plan (manual prod apply)
1. Apply **0005** then **0006** on prod (operator, RUNBOOK) BEFORE shipping any API that reads them.
2. Ship GYM-86a (resolver centralization + exact→name_key cleanup) — deployable independently, no override
   behavior yet (safe consistency win).
3. Ship GYM-86 (override-aware resolve + effective-name display + rename-canonical frontend) — behind tests.
4. Ship GYM-87 consumers / GYM-89 (Link) + GYM-88 (merge) per tax-linking sequencing.

## Risk
22 scattered touch-points, no serializer, and this is the layer that caused the tax-fixes bug class. Build
behind exhaustive tests (rename-global → log → PR/history correct + no split; variant-name resolves; cross-
user sees canonical name; collisions 409). Held until operator review + prod migration. Do NOT auto-deploy.

## Operator decisions (2026-06-08)
- **Fork 1 (shared-surface display):** ratings/leaderboards show the CANONICAL name (e.g. "Bench Press"),
  never a user's private alias. Confirmed.
- **Fork 2a (reset):** add a "Reset to original name" action (deletes the override row → reverts to the
  canonical name), AND gate the whole rename-canonical feature behind a config flag
  (`FEATURE_CANONICAL_RENAME`) so it can be switched off without a code rollback. Confirmed.
- **Fork 2b (Link):** Link-a-custom-to-canonical is triggered via long-tap (manage sheet action) on an own
  custom exercise, picking a canonical in the SAME muscle. **UX caveat (agreed): Link has no payoff until
  ratings exist — ship Link WITH ratings (GYM-13/competition), not standalone.**
- **Scope decision:** GYM-86 (rename-canonical) + tax-linking (GYM-88 merge, GYM-89 Link) are DEFERRED on
  YAGNI grounds (single-user app today; ratings/AI are Phase 6/7). The structural debt that made this risky
  (name resolution/display scattered across ~22 sites, no shared helper) is addressed SEPARATELY and now by
  **GYM-106** (centralize the resolver + a name-projection seam) — hardening, not avoidance.

## Status / next
Status: **accepted (design) / DEFERRED (build)**. Schema (0005/0006) authored + tested + HELD on branch
`tax-canonical/foundation`; this ADR records the design + decisions. GYM-86/87/88/89 → deferred (backlog).
GYM-106 (resolver centralization, no migration) proceeds now as the de-fragmentation step. Resume the
canonical build when ratings/AI are actually being built (or the rename-need recurs) — apply 0005/0006 to
prod first, then GYM-86 behind the feature flag + exhaustive tests.
