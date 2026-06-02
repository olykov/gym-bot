"""FastAPI dependencies for authentication and authorization.

Provides two independent auth paths:

1. ``get_principal`` — unified bot-facing dependency.  Resolves an effective
   principal from EITHER a user JWT (``Authorization: Bearer <token>``) OR a
   service identity (``X-Service-Token`` + ``X-Act-As-User``).  Used by all
   bot-facing routers so that both the Mini App (user JWT) and the bot service
   (impersonation) can call the same endpoints.

   ``get_principal`` is a yield dependency so that per-request state is
   properly scoped.  The RLS GUC context is injected via ``session.info`` by
   ``get_db_for_principal`` (GYM-37) — contextvars are no longer used for GUC
   wiring so there is no threadpool-propagation issue.

2. ``require_admin`` — admin-only gate.  Validates a JWT and asserts the
   ``role == "admin"`` claim.  The service token path is explicitly excluded;
   a service-authenticated caller can NEVER reach admin routes.

   Admin routes use ``get_db_for_admin`` (from ``app.core.database``) which
   synthesises a role='admin' principal for the RLS GUC injection.

H1 fix (GYM-37): ``get_current_user`` / ``require_role`` / ``require_admin``
are now yield-based with a no-op ``finally`` block, ensuring they properly
bracket the request lifetime.  No stale principal context can persist on a
pooled thread because RLS state lives on the per-request Session (session.info)
which is discarded when the session closes.
"""
import hmac
import logging
from typing import Generator, Optional, TypedDict

from fastapi import Header, HTTPException

from app.core.auth import verify_session_token
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Principal(TypedDict):
    """Resolved identity for a single API request.

    Attributes:
        user_id: Effective Telegram user id.  Single source for all per-user
            scoping.  Wired into the RLS GUC via ``session.info`` in
            ``get_db_for_principal`` (GYM-37 session.info approach).
        role: Either ``"user"`` or ``"admin"``.  Service-impersonated callers
            always receive ``"user"`` regardless of any claim in the request.
    """

    user_id: int
    role: str


def get_principal(
    authorization: Optional[str] = Header(None),
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
    x_act_as_user: Optional[str] = Header(None, alias="X-Act-As-User"),
) -> Generator[Principal, None, None]:
    """Resolve the effective principal for a request.

    Yield-based dependency.  Tries the service-token path first; falls back
    to JWT Bearer.

    Service-token path (bot impersonation):
        - ``X-Service-Token`` must match ``settings.BOT_SERVICE_TOKEN``
          (constant-time compare via ``hmac.compare_digest``).
        - ``X-Act-As-User`` must be present and a valid integer Telegram id.
        - Effective role is ALWAYS ``"user"``; a service caller can never
          become admin via this path.

    JWT Bearer path (Mini App / web):
        - ``Authorization: Bearer <token>`` is verified with the JWT secret.
        - Role is taken from the ``role`` claim inside the token.

    RLS GUC context:
        GUC injection is done by ``get_db_for_principal`` (which depends on
        this dep) via ``session.info`` — NOT by contextvars.  This avoids the
        threadpool-propagation issue where a contextvar set in the dep's
        threadpool call is not visible in the endpoint body's threadpool call
        (proved by GYM-37 integration tests).

    Args:
        authorization: ``Authorization`` header value (optional).
        x_service_token: ``X-Service-Token`` header value (optional).
        x_act_as_user: ``X-Act-As-User`` header value (optional).

    Yields:
        Principal dict with ``user_id`` (int) and ``role`` (str).

    Raises:
        HTTPException 400: ``X-Service-Token`` matched but ``X-Act-As-User``
            is missing or not a valid integer.
        HTTPException 401: No valid credential provided, or JWT is invalid /
            expired.
    """
    settings = get_settings()
    principal = _resolve_principal(settings, authorization, x_service_token, x_act_as_user)
    yield principal
    # Reason: no contextvar reset needed — RLS state lives on session.info
    # (discarded when the Session closes).  The yield boundary still properly
    # scopes the dependency lifetime for FastAPI's exit-stack teardown.


def _resolve_principal(
    settings: object,
    authorization: Optional[str],
    x_service_token: Optional[str],
    x_act_as_user: Optional[str],
) -> Principal:
    """Resolve principal from headers without touching contextvars.

    Args:
        settings: Loaded Settings instance.
        authorization: Authorization header value.
        x_service_token: X-Service-Token header value.
        x_act_as_user: X-Act-As-User header value.

    Returns:
        Resolved Principal.

    Raises:
        HTTPException 400 / 401: On auth failure.
    """
    # --- Service-token path ---------------------------------------------------
    if x_service_token is not None:
        token_ok = hmac.compare_digest(
            x_service_token.encode("utf-8"),
            settings.BOT_SERVICE_TOKEN.encode("utf-8"),
        )
        if not token_ok:
            logger.warning("get_principal: invalid X-Service-Token received")
            raise HTTPException(status_code=401, detail="Invalid service token")

        if not x_act_as_user:
            raise HTTPException(
                status_code=400,
                detail="X-Act-As-User header is required when using X-Service-Token",
            )

        try:
            user_id = int(x_act_as_user)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="X-Act-As-User must be a valid integer Telegram user id",
            )

        logger.debug("get_principal: service auth, acting as user_id=%d", user_id)
        # Service callers always resolve as 'user' — never admin.
        return Principal(user_id=user_id, role="user")

    # --- JWT Bearer path ------------------------------------------------------
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[len("Bearer "):]
    claims = verify_session_token(token)

    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid identity in token")

    role = claims.get("role", "user")
    logger.debug("get_principal: JWT auth, user_id=%d role=%s", user_id, role)
    return Principal(user_id=user_id, role=role)


# ---------------------------------------------------------------------------
# Legacy / admin dependencies (H1 fix: now yield-based — GYM-37)
#
# These dependencies are yield-based so FastAPI's exit-stack properly brackets
# their lifetime.  No contextvar manipulation is done here — RLS state lives
# on session.info (set by get_db_for_admin / get_db_for_principal) and is
# discarded when the Session closes.  Making them yield-based guarantees no
# stale principal can persist on a reused worker thread between requests.
# ---------------------------------------------------------------------------


def get_current_user(
    authorization: str = Header(None),
) -> Generator[dict, None, None]:
    """Extract and verify user from Authorization Bearer header.

    Yield-based (H1 fix): the dependency lifetime is properly scoped to the
    request.  No contextvar mutation — RLS context is set via session.info.

    Args:
        authorization: Authorization header value.

    Yields:
        Decoded JWT claims dict.

    Raises:
        HTTPException 401: If token is missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    user_data = verify_session_token(token)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    yield user_data
    # Reason: finally block is implicit in generator deps; no state to reset
    # since RLS GUC lives on session.info (discarded at session.close()).


def require_role(required_role: str):
    """Return a dependency that enforces a specific role.

    The returned dependency is yield-based (H1 fix) — it brackets the full
    request lifetime, guaranteeing no stale principal on a pooled thread.

    RLS context for admin routes is set via ``get_db_for_admin`` (session.info)
    rather than here.

    Args:
        required_role: Required role string (``"admin"`` or ``"user"``).

    Returns:
        FastAPI generator dependency that yields the user dict when authorized.
    """

    def role_checker(authorization: str = Header(None)) -> Generator[dict, None, None]:
        """Check role and yield JWT claims.

        Args:
            authorization: Authorization header value.

        Yields:
            Decoded JWT claims dict.

        Raises:
            HTTPException 401: Token missing or invalid.
            HTTPException 403: Role does not match required_role.
        """
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.replace("Bearer ", "")
        user_data = verify_session_token(token)

        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if user_data.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {required_role}",
            )

        yield user_data
        # Reason: no state to reset; RLS lives on session.info per GYM-37.

    return role_checker


def require_admin(authorization: str = Header(None)) -> Generator[dict, None, None]:
    """Require an admin-role JWT.  Not reachable via service token.

    Yield-based (H1 fix).  RLS admin context (``app.role='admin'``) is injected
    via ``get_db_for_admin`` (session.info), not here.

    Args:
        authorization: Authorization header value.

    Yields:
        Decoded JWT claims for the admin user.

    Raises:
        HTTPException 401: Token missing or invalid.
        HTTPException 403: Role is not 'admin'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    user_data = verify_session_token(token)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Required role: admin")

    yield user_data
    # Reason: no state to reset; RLS lives on session.info per GYM-37.


def require_user(authorization: str = Header(None)) -> Generator[dict, None, None]:
    """Require any authenticated user JWT (legacy; prefer get_principal).

    Yield-based (H1 fix).

    Args:
        authorization: Authorization header value.

    Yields:
        Decoded JWT claims.
    """
    yield from get_current_user(authorization)
