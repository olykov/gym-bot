# api-contract

OpenAPI specification for the Core API plus generated typed clients (TypeScript and Python).

This is the **source of truth** for the contract between the Core API (`apps/api`) and every
client (bot, web, miniapp, admin, future mobile). Clients are generated from the spec here and
**must be regenerated when the spec changes**.

- Spec: [`openapi.yaml`](openapi.yaml) — OpenAPI 3.1.
- The contract is additive and minimal (YAGNI): it covers only operations that exist today.

## Layout

```
openapi.yaml                          # single source of truth
Makefile                              # validate + generate clients
scripts/validate.py                   # OpenAPI 3.1 validator
clients/python/                       # installable async client package (gym-api-client)
  pyproject.toml                      #   package metadata (pip install target)
  gym_api_client/models.py            #   generated pydantic v2 models (make gen-python)
  gym_api_client/client.py            #   hand-maintained async httpx wrapper (GymApiClient)
clients/typescript/                   # generated TS types (gitignored; regenerate on demand)
```

## Authentication

Two security schemes are defined in `components.securitySchemes`:

- **`userJwt`** — `http`/`bearer` JWT. A per-user session token issued by the `/auth/*`
  endpoints, sent as `Authorization: Bearer <token>`. Per-user scoping is derived from the
  authenticated identity (`sub` claim). Used by web/miniapp/admin.
- **`serviceAuth`** — `apiKey` in header `X-Service-Token`. A service-to-service token
  identifying a trusted backend (the bot). A service request MUST also carry the companion
  header **`X-Act-As-User`** (the integer Telegram id the service acts on behalf of), modeled
  as the reusable `ActAsUser` header parameter on each bot-facing operation. Scoping comes from
  `X-Act-As-User` instead of a JWT `sub` claim.

**Who accepts what:**

- **Bot-facing operations** (`/users/me`, `/muscles*`, `/exercises*`, `/training*`,
  `/analytics/*`) accept **either** scheme: `security: [{userJwt: []}, {serviceAuth: []}]`,
  and declare the optional `X-Act-As-User` header.
- **Admin operations** (`/admin/*`) and `GET /auth/me` keep **`userJwt` only** (the global
  default).
- Only `POST /auth/*` (token issuance) is unauthenticated (`security: []`).

Clients never pass `user_id` in the body or query; identity comes from the token (`userJwt`)
or `X-Act-As-User` (`serviceAuth`).

## Python client for the bot

`clients/python/` is an installable package (`gym-api-client`) providing a **usable async
httpx client**, not just models:

- `gym_api_client.models` — pydantic v2 models, **generated** from the spec (`make gen-python`).
- `gym_api_client.GymApiClient` — a thin **hand-maintained** async wrapper with one method per
  bot-facing operation and per-client / per-request custom-header injection.

Import path: `from gym_api_client import GymApiClient, models`. Install with
`pip install packages/api-contract/clients/python`.

The bot injects the service-auth headers like this:

```python
from gym_api_client import GymApiClient, models

async with GymApiClient(
    base_url="https://api.example.com/api/v1",
    service_token="<X-Service-Token>",   # set once per client
) as api:
    user = await api.get_me(act_as_user=12345)              # X-Act-As-User per request
    await api.create_training(
        models.TrainingCreate(muscle_name="Chest", exercise_name="Bench Press",
                              set=1, weight=60, reps=10),
        act_as_user=12345,
    )
```

`service_token` (constructor) sets `X-Service-Token` on every request; `act_as_user=<id>`
(per method) sets `X-Act-As-User`. Any header can be overridden per call via `headers={...}`.
For `userJwt`, pass `token="<jwt>"` to the constructor and omit `act_as_user`.

### Operation -> client method map

| Contract operation        | Client method                                          |
|---------------------------|--------------------------------------------------------|
| `getMe`                   | `get_me()`                                              |
| `upsertMe`                | `upsert_me(body)`                                       |
| `listMuscles`             | `list_muscles()`                                        |
| `createMuscle`            | `create_muscle(body)`                                   |
| `listExercisesByMuscle`   | `list_exercises_by_muscle(muscle_id)`                  |
| `createExercise`          | `create_exercise(body)`                                 |
| `hideExercise`            | `hide_exercise(exercise_id)`                            |
| `unhideExercise`          | `unhide_exercise(exercise_id)`                          |
| `deletePrivateExercise`   | `delete_private_exercise(exercise_id)`                  |
| `listTraining`            | `list_training(skip=, limit=)`                          |
| `createTraining`          | `create_training(body)`                                 |
| `updateTraining`          | `update_training(training_id, body)`                    |
| `getCompletedSets`        | `get_completed_sets(muscle=, exercise=, date=)`         |
| `getTrainingHistory`      | `get_training_history(muscle=, exercise=)`              |
| `getPersonalRecord`       | `get_personal_record(muscle=, exercise=)`               |
| `getMaxRepsForWeight`     | `get_max_reps_for_weight(muscle=, exercise=, weight=)`  |
| `getTopExercises`         | `get_top_exercises(muscle=, limit=)`                    |

Every method takes optional `act_as_user: int` and `headers: dict[str, str]`.

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
