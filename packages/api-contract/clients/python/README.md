# gym-api-client

Async Python client for the Gym Tracker Core API contract (`packages/api-contract/openapi.yaml`).

Two parts:

- `gym_api_client.models` — pydantic v2 models, **generated** from the spec
  (`make gen-python` in `packages/api-contract/`). Do not edit by hand.
- `gym_api_client.client.GymApiClient` — a thin, **hand-maintained** async
  `httpx` wrapper with one method per bot-facing operation. It supports
  per-client and per-request custom-header injection so a service (the bot)
  can pass the service-auth headers.

## Install

```bash
pip install /path/to/packages/api-contract/clients/python   # or add as a path dependency
```

## Auth

The bot uses `serviceAuth`: a service token plus the acted-on Telegram id.

```python
from gym_api_client import GymApiClient, models

async with GymApiClient(
    base_url="https://api.example.com/api/v1",
    service_token="<X-Service-Token value>",
) as api:
    # X-Act-As-User is sent per request via act_as_user=<telegram_id>.
    user = await api.get_me(act_as_user=12345)
    await api.create_training(
        models.TrainingCreate(
            muscle_name="Chest", exercise_name="Bench Press",
            set=1, weight=60, reps=10,
        ),
        act_as_user=12345,
    )
```

A per-user JWT (`userJwt`) is also supported: pass `token="<jwt>"` to the
constructor (sets `Authorization: Bearer ...`) and omit `act_as_user`.

Any header can be overridden per request via `headers={...}`.
