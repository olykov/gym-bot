"""FastAPI dependencies for authentication and authorization.

Provides two independent auth paths:

1. ``get_principal`` — unified bot-facing dependency.  Resolves an effective
   principal from EITHER a user JWT (``Authorization: Bearer <token>``) OR a
   service identity (``X-Service-Token`` + ``X-Act-As-User``).  Used by all
   bot-facing routers so that both the Mini App (user JWT) and the bot service
   (impersonation) can call the same endpoints.

   ``get_principal`` is a yield dependency: it sets the RLS GUC contextvars on
   entry and resets them in a ``finally`` block so that thread-pool workers
   never carry a stale principal across requests.

2. ``require_admin`` — admin-only gate.  Validates a JWT and asserts the
   ``role == "admin"`` claim.  The service token path is explicitly excluded;
   a service-authenticated caller can NEVER reach admin routes.

   Admin deps also set the contextvars (role='admin') so that the SQLAlchemy
   ``after_begin`` event injects the correct GUC and RLS lets admins see all rows.
"""
import hmac
import logging
from typing import Generator, Optional, TypedDict

from fastapi import Header, HTTPException

from app.core.auth import verify_session_token
from app.core.config import get_settings
from app.core.db_context import reset_principal_context, set_principal_context

logger = logging.getLogger(__name__)


class Principal(TypedDict):
    """Resolved identity for a single API request.

    Attributes:
        user_id: Effective Telegram user id.  Single source for all per-user
            scoping.  The RLS ``after_begin`` event reads this via contextvar.
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
    """Resolve the effective principal for a request and set RLS GUC context.

    Yield-based dependency: sets ``current_user_id`` / ``current_role``
    contextvars on entry (so the SQLAlchemy ``after_begin`` event picks them
    up) and resets them in a ``finally`` block to avoid stale state on pooled
    threads.

    Tries the service-token path first; falls back to JWT Bearer.

    Service-token path (bot impersonation):
        - ``X-Service-Token`` must match ``settings.BOT_SERVICE_TOKEN``
          (constant-time compare via ``hmac.compare_digest``).
        - ``X-Act-As-User`` must be present and a valid integer Telegram id.
        - Effective role is ALWAYS ``"user"``; a service caller can never
          become admin via this path.

    JWT Bearer path (Mini App / web):
        - ``Authorization: Bearer <token>`` is verified with the JWT secret.
        - Role is taken from the ``role`` claim inside the token.

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
    tokens = set_principal_context(principal["user_id"], principal["role"])
    try:
        yield principal
    finally:
        reset_principal_context(*tokens)


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
# Legacy / admin dependencies — kept for backward compatibility.
# Admin endpoints use require_admin; they are NOT reachable via service token.
# ---------------------------------------------------------------------------


def get_current_user(authorization: str = Header(None)) -> dict:
    """Extract and verify user from Authorization Bearer header.

    Also sets the RLS GUC context as role='user' with the resolved user_id so
    that legacy endpoints (``/user/*``) benefit from the RLS wiring too.

    Note: this is NOT a yield dependency, so the contextvar reset happens
    immediately after the dep returns.  The GUC is set at the start of the
    DB transaction (``after_begin``), which fires after the dependency runs but
    before the route body executes — so the value is read correctly.

    Args:
        authorization: Authorization header value.

    Returns:
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

    # Set GUC context for legacy routes; role from the token claim.
    try:
        uid = int(user_data["sub"])
    except (KeyError, TypeError, ValueError):
        uid = None
    role = user_data.get("role", "user")
    set_principal_context(uid, role)
    # Reason: we do not reset here because the contextvar is thread-local via
    # contextvars and will be overwritten on the next request in the same thread.
    # For legacy endpoints this is acceptable; get_principal (yield) is the
    # preferred pattern for new routes.

    return user_data


def require_role(required_role: str):
    """Return a dependency that enforces a specific role.

    Sets the RLS GUC context with the resolved role so admin-gated routes
    see all rows via the ``app.role = 'admin'`` branch in the RLS policy.

    Args:
        required_role: Required role string (``"admin"`` or ``"user"``).

    Returns:
        FastAPI dependency function that yields the user dict when authorized.
    """

    def role_checker(authorization: str = Header(None)) -> dict:
        user = get_current_user(authorization)

        if user.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {required_role}",
            )

        return user

    return role_checker


def require_admin(authorization: str = Header(None)) -> dict:
    """Require an admin-role JWT.  Not reachable via service token.

    Sets ``current_role = 'admin'`` in the contextvar so the SQLAlchemy
    ``after_begin`` event injects ``app.role = 'admin'`` into the GUC and the
    RLS policy's admin branch allows cross-user reads.

    Args:
        authorization: Authorization header value.

    Returns:
        Decoded JWT claims for the admin user.
    """
    return require_role("admin")(authorization)


def require_user(authorization: str = Header(None)) -> dict:
    """Require any authenticated user JWT (legacy; prefer get_principal).

    Args:
        authorization: Authorization header value.

    Returns:
        Decoded JWT claims.
    """
    return get_current_user(authorization)
