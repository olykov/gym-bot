"""Async httpx client for the Gym Tracker Core API contract.

Thin, hand-maintained wrapper over the generated pydantic models
(:mod:`gym_api_client.models`). It exposes one ``async`` method per bot-facing
operation and supports custom-header injection so a service (the bot) can pass
the service-auth headers ``X-Service-Token`` and ``X-Act-As-User`` either once
per client or per request.

Authentication (see openapi.yaml ``securitySchemes``):

* ``userJwt`` — per-user bearer token. Pass ``token="..."`` to the constructor,
  or set the ``Authorization`` header per request via ``headers=...``.
* ``serviceAuth`` — service token. Pass ``service_token="..."`` to the
  constructor; supply the acted-on user per call via ``act_as_user=<telegram_id>``
  (sent as the ``X-Act-As-User`` header).

Example::

    from gym_api_client import GymApiClient

    async with GymApiClient(
        base_url="https://api.example.com/api/v1",
        service_token="s3cr3t",
    ) as api:
        # The bot acts on behalf of a specific Telegram user per request.
        muscles = await api.list_muscles(act_as_user=12345)
        me = await api.get_me(act_as_user=12345)
"""

from __future__ import annotations

from typing import Any

import httpx

from . import models

SERVICE_TOKEN_HEADER = "X-Service-Token"
ACT_AS_USER_HEADER = "X-Act-As-User"


class GymApiClient:
    """Async client exposing one method per bot-facing contract operation.

    Args:
        base_url: Root URL including the ``/api/v1`` prefix.
        token: Optional per-user JWT, sent as ``Authorization: Bearer <token>``.
        service_token: Optional service token, sent as ``X-Service-Token``.
        headers: Extra default headers merged into every request.
        client: Optional pre-built ``httpx.AsyncClient`` (for testing / reuse).
        timeout: Request timeout in seconds when building the default client.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        service_token: str | None = None,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        default_headers: dict[str, str] = dict(headers or {})
        if token:
            default_headers["Authorization"] = f"Bearer {token}"
        if service_token:
            default_headers[SERVICE_TOKEN_HEADER] = service_token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=default_headers,
            timeout=timeout,
        )

    async def __aenter__(self) -> "GymApiClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying client if this wrapper created it."""
        if self._owns_client:
            await self._client.aclose()

    # ---- internals ----------------------------------------------------------
    @staticmethod
    def _merge_headers(
        act_as_user: int | None,
        headers: dict[str, str] | None,
    ) -> dict[str, str] | None:
        """Build per-request headers from ``act_as_user`` plus explicit overrides."""
        merged: dict[str, str] = {}
        if act_as_user is not None:
            merged[ACT_AS_USER_HEADER] = str(act_as_user)
        if headers:
            merged.update(headers)
        return merged or None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )
        response = await self._client.request(
            method,
            path,
            params=clean_params,
            json=json,
            headers=self._merge_headers(act_as_user, headers),
        )
        response.raise_for_status()
        return response

    # ---- users --------------------------------------------------------------
    async def get_me(
        self, *, act_as_user: int | None = None, headers: dict[str, str] | None = None
    ) -> models.User:
        """getMe — GET /users/me."""
        r = await self._request(
            "GET", "/users/me", act_as_user=act_as_user, headers=headers
        )
        return models.User.model_validate(r.json())

    async def upsert_me(
        self,
        body: models.UserRegistration,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.User:
        """upsertMe — PUT /users/me."""
        r = await self._request(
            "PUT",
            "/users/me",
            json=body.model_dump(mode="json", exclude_none=True),
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.User.model_validate(r.json())

    # ---- muscles ------------------------------------------------------------
    async def list_muscles(
        self, *, act_as_user: int | None = None, headers: dict[str, str] | None = None
    ) -> list[models.Muscle]:
        """listMuscles — GET /muscles."""
        r = await self._request(
            "GET", "/muscles", act_as_user=act_as_user, headers=headers
        )
        return [models.Muscle.model_validate(m) for m in r.json()]

    async def create_muscle(
        self,
        body: models.MuscleCreate,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.Muscle:
        """createMuscle — POST /muscles."""
        r = await self._request(
            "POST",
            "/muscles",
            json=body.model_dump(mode="json"),
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.Muscle.model_validate(r.json())

    # ---- exercises ----------------------------------------------------------
    async def list_exercises_by_muscle(
        self,
        muscle_id: int,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[models.Exercise]:
        """listExercisesByMuscle — GET /muscles/{muscle_id}/exercises."""
        r = await self._request(
            "GET",
            f"/muscles/{muscle_id}/exercises",
            act_as_user=act_as_user,
            headers=headers,
        )
        return [models.Exercise.model_validate(e) for e in r.json()]

    async def create_exercise(
        self,
        body: models.ExerciseCreate,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.Exercise:
        """createExercise — POST /exercises."""
        r = await self._request(
            "POST",
            "/exercises",
            json=body.model_dump(mode="json"),
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.Exercise.model_validate(r.json())

    async def hide_exercise(
        self,
        exercise_id: int,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """hideExercise — PUT /exercises/{exercise_id}/hidden."""
        await self._request(
            "PUT",
            f"/exercises/{exercise_id}/hidden",
            act_as_user=act_as_user,
            headers=headers,
        )

    async def unhide_exercise(
        self,
        exercise_id: int,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """unhideExercise — DELETE /exercises/{exercise_id}/hidden."""
        await self._request(
            "DELETE",
            f"/exercises/{exercise_id}/hidden",
            act_as_user=act_as_user,
            headers=headers,
        )

    async def delete_private_exercise(
        self,
        exercise_id: int,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """deletePrivateExercise — DELETE /exercises/{exercise_id}."""
        await self._request(
            "DELETE",
            f"/exercises/{exercise_id}",
            act_as_user=act_as_user,
            headers=headers,
        )

    # ---- training -----------------------------------------------------------
    async def list_training(
        self,
        *,
        skip: int | None = None,
        limit: int | None = None,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[models.Training]:
        """listTraining — GET /training."""
        r = await self._request(
            "GET",
            "/training",
            params={"skip": skip, "limit": limit},
            act_as_user=act_as_user,
            headers=headers,
        )
        return [models.Training.model_validate(t) for t in r.json()]

    async def create_training(
        self,
        body: models.TrainingCreate,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.Training:
        """createTraining — POST /training."""
        r = await self._request(
            "POST",
            "/training",
            json=body.model_dump(mode="json"),
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.Training.model_validate(r.json())

    async def update_training(
        self,
        training_id: str,
        body: models.TrainingUpdate,
        *,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.Training:
        """updateTraining — PUT /training/{training_id}."""
        r = await self._request(
            "PUT",
            f"/training/{training_id}",
            json=body.model_dump(mode="json"),
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.Training.model_validate(r.json())

    # ---- analytics ----------------------------------------------------------
    async def get_completed_sets(
        self,
        *,
        muscle: str,
        exercise: str,
        date: str,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.CompletedSets:
        """getCompletedSets — GET /analytics/completed-sets."""
        r = await self._request(
            "GET",
            "/analytics/completed-sets",
            params={"muscle": muscle, "exercise": exercise, "date": date},
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.CompletedSets.model_validate(r.json())

    async def get_log_context(
        self,
        *,
        muscle: str,
        exercise: str,
        date: str,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.LogContext:
        """getLogContext — GET /analytics/log-context."""
        r = await self._request(
            "GET",
            "/analytics/log-context",
            params={"muscle": muscle, "exercise": exercise, "date": date},
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.LogContext.model_validate(r.json())

    async def get_training_history(
        self,
        *,
        muscle: str,
        exercise: str,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[models.TrainingHistoryEntry]:
        """getTrainingHistory — GET /analytics/history."""
        r = await self._request(
            "GET",
            "/analytics/history",
            params={"muscle": muscle, "exercise": exercise},
            act_as_user=act_as_user,
            headers=headers,
        )
        return [models.TrainingHistoryEntry.model_validate(h) for h in r.json()]

    async def get_personal_record(
        self,
        *,
        muscle: str,
        exercise: str,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.PersonalRecord | None:
        """getPersonalRecord — GET /analytics/personal-record."""
        r = await self._request(
            "GET",
            "/analytics/personal-record",
            params={"muscle": muscle, "exercise": exercise},
            act_as_user=act_as_user,
            headers=headers,
        )
        payload = r.json()
        return models.PersonalRecord.model_validate(payload) if payload else None

    async def get_max_reps_for_weight(
        self,
        *,
        muscle: str,
        exercise: str,
        weight: float,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> models.MaxReps:
        """getMaxRepsForWeight — GET /analytics/max-reps."""
        r = await self._request(
            "GET",
            "/analytics/max-reps",
            params={"muscle": muscle, "exercise": exercise, "weight": weight},
            act_as_user=act_as_user,
            headers=headers,
        )
        return models.MaxReps.model_validate(r.json())

    async def get_top_exercises(
        self,
        *,
        muscle: str,
        limit: int | None = None,
        act_as_user: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[models.TopExercise]:
        """getTopExercises — GET /analytics/top-exercises."""
        r = await self._request(
            "GET",
            "/analytics/top-exercises",
            params={"muscle": muscle, "limit": limit},
            act_as_user=act_as_user,
            headers=headers,
        )
        return [models.TopExercise.model_validate(t) for t in r.json()]
