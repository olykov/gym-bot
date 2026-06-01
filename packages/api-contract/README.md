# api-contract

OpenAPI specification for the Core API plus generated typed clients (TypeScript and Python).

This is the **source of truth** for the contract between the Core API (`apps/api`) and every
client (bot, web, miniapp, admin, future mobile). Clients are generated from the spec here and
**must be regenerated when the spec changes**.

- Spec: [`openapi.yaml`](openapi.yaml) — OpenAPI 3.1.
- The contract is additive and minimal (YAGNI): it covers only operations that exist today.

## Layout

```
openapi.yaml                       # single source of truth
Makefile                           # validate + generate clients
scripts/validate.py                # OpenAPI 3.1 validator
clients/python/gym_api_client/     # generated pydantic v2 models (for the bot, Phase 3)
clients/typescript/                # generated TS types (gitignored; regenerate on demand)
```

## Authentication

A session JWT issued by the `/auth/*` endpoints, sent as `Authorization: Bearer <token>`.
**Per-user scoping is derived from the authenticated identity** (`sub` claim) — clients never
pass `user_id` in the body or query. Only the `/auth/*` endpoints are unauthenticated.

## Generating clients

Requires `uv` (Python tooling) and `npx`/`node` (TypeScript tooling).

```bash
make validate        # validate openapi.yaml against the OpenAPI 3.1 schema
make gen-python      # pydantic v2 models -> clients/python/gym_api_client/models.py
make gen-typescript  # TS types          -> clients/typescript/schema.ts
make gen             # both clients
make all             # validate + both clients
```

Under the hood:

- **Python** uses [`datamodel-code-generator`](https://github.com/koxudaxi/datamodel-code-generator)
  to emit pydantic v2 models. A sample (`clients/python/gym_api_client/models.py`) is committed to
  prove the pipeline; Phase 3 wires these into the bot.
- **TypeScript** uses [`openapi-typescript`](https://github.com/openapi-ts/openapi-typescript) to
  emit `paths`/`components` types for web/admin/miniapp. The output is gitignored — regenerate with
  `make gen-typescript` (kept out of the tree to avoid vendoring large generated files).

## Coverage — bot DB methods mapped to the contract

Every public method of `apps/bot/modules/postgres.py` (the bot's current data layer) maps to a
contract operation, so Phase 3 can move the bot off direct SQL:

| Bot DB method                          | Contract operation                                  |
|----------------------------------------|-----------------------------------------------------|
| `get_user(user_id)`                    | `GET /users/me`                                     |
| registration via `save_any_data("users", …)` | `PUT /users/me` (`upsertMe`)                   |
| `get_all_muscles(user_id)`             | `GET /muscles`                                      |
| `add_muscle(name, user_id)`            | `POST /muscles`                                     |
| `get_exercises_by_muscle(muscle, user_id)` | `GET /muscles/{muscle_id}/exercises`            |
| `add_exercise(name, muscle, user_id)`  | `POST /exercises`                                   |
| `hide_exercise(user_id, ex, muscle)`   | `PUT /exercises/{exercise_id}/hidden`               |
| `delete_private_exercise(user_id, ex, muscle)` | `DELETE /exercises/{exercise_id}`           |
| `get_top_exercises_for_muscle(user_id, muscle, limit)` | `GET /analytics/top-exercises`      |
| `save_training_data(…)`                | `POST /training`                                    |
| `update_training_data(id, user_id, w, r)` | `PUT /training/{training_id}`                    |
| `get_completed_sets(user, muscle, ex, date)` | `GET /analytics/completed-sets`               |
| `get_last_training_history(user, muscle, ex)` | `GET /analytics/history`                     |
| `get_personal_record(user, muscle, ex)`| `GET /analytics/personal-record`                   |
| `get_max_reps_for_weight(user, muscle, ex, weight)` | `GET /analytics/max-reps`              |

Admin/user endpoints already in `apps/api` are also covered: `POST/PUT /admin/muscles`,
`POST/PUT /admin/exercises`, `GET /admin/training`, `GET /admin/static-data`, the `/auth/*`
endpoints, and `GET /training`.

### Coverage gaps and notes

- **`get_latest_training(user_id, body_part, exercise)`** (bot) is **not** given a dedicated
  endpoint. It is the only analytics read keyed on `muscles.body_part` (a column not modeled in
  `apps/api`), and it is functionally subsumed by `GET /analytics/history` (which returns the same
  date/set/weight/reps shape, newest first). Flagged here rather than speculatively modeling
  `body_part`. If Phase 3 needs it verbatim, add a `body_part` query variant — additive.
- **Hide/unhide and delete for muscles** (`PUT/DELETE /muscles/{muscle_id}/hidden`,
  `DELETE /muscles/{muscle_id}`) are defined for parity with exercises, but the bot does **not**
  currently expose muscle hide/delete operations. They are additive and safe; remove them if they
  stay unused after Phase 3.
- Muscle/exercise **names vs ids**: the bot resolves by name today. Create/analytics request bodies
  take names (`muscle_name`, `exercise_name`) to match the bot 1:1; resources are addressed by id
  in paths. Responses always include the canonical id.

## Change policy

- **Additive** (new path, new optional field): safe.
- **Breaking** (rename/remove a field or path, add a required field): call it out explicitly with
  per-client migration impact, and **regenerate both clients in the same change**. A contract
  change is incomplete until the generated clients match.
