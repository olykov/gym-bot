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

| Schema | Field | Kind | maxLength |
|--------|-------|------|-----------|
| `MuscleCreate` | `name` | muscle | 30 |
| `ExerciseCreate` | `name` | exercise | 40 |
| `ExerciseCreate` | `muscle_name` | muscle | 30 |
| `AdminExerciseCreate` | `name` | exercise | 40 |
| `TrainingCreate` | `muscle_name` | muscle | 30 |
| `TrainingCreate` | `exercise_name` | exercise | 40 |

Each field also has `minLength: 1` and the canonical `pattern` above.
