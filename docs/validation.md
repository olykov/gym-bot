# Input validation rules

Canonical, shared validation rules for user-supplied input across the platform. This is the
**single source of truth** cited by both layers:

- the **Core API** (`apps/api`) enforces these rules and returns HTTP 422 on violation;
- the **frontend** clients (Mini App `apps/web`, admin, bot) mirror them for inline feedback.

The rules are also encoded in the contract (`packages/api-contract/openapi.yaml`) as
`minLength` / `maxLength` / `pattern` on the relevant request schemas, so generated clients
carry them automatically.

This document grows by appending a new section per field family (numeric inputs, other
free-text, etc.). Keep each rule set in its own table.

---

## Name rules

Applies to every **muscle** and **exercise** name accepted on input (create / rename, any
client).

### Normalization (applied before validation)

1. Trim leading and trailing whitespace.
2. Collapse every run of internal whitespace to a single ASCII space.

Validation below is performed on the **normalized** value.

### Create vs lookup

Length and allowed-character limits apply **only to a name being created/stored**, never to a
name used to **look up an existing record**:

- **Create-name** field — the field that *names the thing being created* (a new muscle or a new
  exercise). Full rules: `minLength`, `maxLength`, and the allowed-character `pattern`. Example:
  `MuscleCreate.name`, `ExerciseCreate.name`, `AdminExerciseCreate.name`.
- **Lookup-reference** field — the field that *references an existing muscle/exercise by name*
  (e.g. the owning muscle when adding an exercise, or the muscle/exercise when logging a set).
  **Normalized only** (trim + collapse), with `minLength: 1` to reject empty/whitespace-only. No
  `maxLength`, no `pattern` — otherwise you could never reference data that predates the rules
  (e.g. a muscle whose name is longer than 30 chars). Lookups go through parameterized SQL and a
  non-matching value 404s at the DB, so they need no char-whitelist. Example:
  `ExerciseCreate.muscle_name`, `TrainingCreate.muscle_name`, `TrainingCreate.exercise_name`.

The rules in this section (max length, allowed characters) describe **create-name** fields.
Lookup-reference fields take only normalization + `minLength: 1`.

### Rules

| Rule | Muscle name | Exercise name |
|------|-------------|---------------|
| Min length (after normalize) | 1 | 1 |
| Max length (after normalize) | 30 | 40 |
| Empty / whitespace-only | rejected | rejected |
| Allowed characters | see allowed-set below | see allowed-set below |

### Allowed characters

| Class | Allowed |
|-------|---------|
| Letters | Unicode letters `\p{L}` (Latin, **Cyrillic**, any script) |
| Digits | Unicode digits `\p{N}` |
| Space | single ASCII space (after normalization) |
| Punctuation | `-` `'` `.` `,` `(` `)` `/` `&` `+` `°` (degree sign) |

Everything else is **rejected**, including control characters, emoji, and the markup/shell
metacharacters `< > { } [ ] | \ ^ ~ $ @ #`. Rejecting these also keeps names safe to render in
Telegram HTML / Markdown without escaping surprises.

### Canonical regex

Anchored, Unicode-aware character class (ECMA-262 with the `u` flag; equivalently the Rust
`regex` engine used by pydantic v2):

```
^[\p{L}\p{N} \-'.,()/&+°]+$
```

This is the exact `pattern` carried by the contract schemas below. The Unicode property escapes
`\p{L}` / `\p{N}` are supported by the contract validator (OpenAPI 3.1), by `openapi-typescript`
(types only, no runtime enforcement), and by pydantic v2's regex engine — so the generated
Python and TypeScript clients build without a Unicode-escape compromise.

> Note: the `pattern` enforces the allowed-character set and length bounds. Normalization
> (trim + whitespace collapse) is a server-side pre-step, not expressible in a JSON-Schema
> `pattern`; clients should normalize before sending, and the Core API normalizes on receipt.

### Where it is enforced in the contract

`packages/api-contract/openapi.yaml` request schemas carrying a muscle/exercise name:

| Schema | Field | Kind | Role | minLength | maxLength | pattern |
|--------|-------|------|------|-----------|-----------|---------|
| `MuscleCreate` | `name` | muscle | create | 1 | 30 | yes |
| `ExerciseCreate` | `name` | exercise | create | 1 | 40 | yes |
| `ExerciseCreate` | `muscle_name` | muscle | lookup | 1 | — | — |
| `AdminExerciseCreate` | `name` | exercise | create | 1 | 40 | yes |
| `TrainingCreate` | `muscle_name` | muscle | lookup | 1 | — | — |
| `TrainingCreate` | `exercise_name` | exercise | lookup | 1 | — | — |

**Create** fields carry `minLength: 1`, `maxLength`, and the canonical `pattern` above.
**Lookup** fields carry only `minLength: 1` (normalized server-side; no `maxLength`, no
`pattern`) — see "Create vs lookup" above.

---

## Dedup key (`name_key`) — lexical de-duplication

> Distinct from the **display normalization** above. Display normalization (trim + collapse
> whitespace) decides *what gets stored* in `name`. The **dedup key** decides *which names count
> as the same thing* for uniqueness. "Bench Press", "bench-press", "bench_press", and
> "BENCH  PRESS" are stored with their own display names but collapse to **one** `name_key`, so
> only one can exist per scope. (ADR 0001, layer 2a — lexical dedup.)

### Canonical key function — `app_name_key(text)`

The match key is computed by **one** IMMUTABLE Postgres SQL function,
`public.app_name_key(text)`, installed by migration
`packages/db/alembic/versions/0004_name_key.py` (GYM-84) and mirrored in
`packages/db/init.sql`. It is the **single source of truth**:

- the DB backs `muscles.name_key` and `exercises.name_key`
  (`GENERATED ALWAYS AS (app_name_key(name)) STORED`) and the partial UNIQUE indexes with it;
- the Core API (`apps/api`) MUST call this same function for write-path lookups (GYM-85) — never
  re-implement the key in application code, or the API and DB can disagree and let a duplicate
  slip in (or wrongly 404 a real match).

### Normalization steps (in order)

Applied to a name to derive its `name_key`:

1. **Lowercase** — `lower()`. (Postgres `lower()` folds Cyrillic correctly, e.g. `Ё`→`ё`. Full
   Unicode casefold is **not** used — `lower()` is sufficient for the Latin/Cyrillic catalog.)
2. **Unify separators** — hyphen `-` and underscore `_` are replaced with a space.
3. **Strip incidental punctuation** — apostrophes (`'` and `` ` ``), dots `.`, and commas `,` are
   removed (so `O'Brien's` and `OBriens` share a key; `v2.0` → `v20`).
4. **Collapse whitespace** — every run of whitespace becomes a single ASCII space.
5. **Trim** — leading/trailing whitespace removed.

Examples:

| Input | `name_key` |
|-------|------------|
| `Bench Press` / `bench-press` / `bench_press` / `BENCH  PRESS` | `bench press` |
| `  O'Brien's  Curl... ` | `obriens curl` |
| `Жим  Лёжа` | `жим лёжа` |
| `Push-Up, v2.0` | `push up v20` |

**Accent-folding is intentionally NOT applied.** The `unaccent` extension is not used: accent
differences are rare in this catalog and would add an extension dependency plus an IMMUTABLE-wrapper
requirement for marginal benefit. This can be layered into `app_name_key` later if a real need
appears (a single function change then propagates to both the generated columns and the API).

### Uniqueness scope

`name_key` uniqueness mirrors the original name-based partial unique indexes:

| Table | Global rows (`created_by IS NULL`) | User rows (`created_by IS NOT NULL`) |
|-------|------------------------------------|--------------------------------------|
| `muscles` | UNIQUE `(name_key)` | UNIQUE `(name_key, created_by)` |
| `exercises` | UNIQUE `(name_key, muscle)` | UNIQUE `(name_key, muscle, created_by)` |

The earlier `name`-based unique indexes were dropped — the `name_key` uniques subsume them.

> **Note for GYM-85 (API write path):** on create/rename, normalize the incoming name to its
> key with `app_name_key` and check the visible set before inserting. Per ADR 0001, a key match
> resolves to the existing row (silently unhiding a hidden one) rather than blindly creating a
> duplicate; adding a name whose key already matches a *visible* row of yours is rejected.
