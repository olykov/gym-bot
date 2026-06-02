"""SQLAlchemy engine, session factory, and RLS GUC wiring.

The runtime engine connects as ``app_rw`` (NOSUPERUSER NOBYPASSRLS) so that
Postgres RLS policies take effect.  The superuser ``DATABASE_URL`` (myuser) is
kept in config for Alembic and ops tooling only — never used here.

RLS GUC injection — session.info approach (GYM-37):
    ``get_db`` accepts the resolved principal and stashes it on the session:

        session.info['app_user_id'] = str(principal['user_id']) or ''
        session.info['app_role']    = principal['role'] or ''

    A ``Session after_begin`` event listener runs at the start of every
    transaction and reads from ``session.info`` (NOT from contextvars) to emit:

        SELECT set_config('app.user_id', :uid, true),
               set_config('app.role',    :role, true)

    with ``is_local=true`` so the values reset automatically at transaction end,
    preventing any leakage across pooled connections.

    Why session.info, not contextvars (GYM-37):
        FastAPI runs each sync dependency and the sync endpoint body in SEPARATE
        ``anyio.to_thread.run_sync`` calls, each receiving its own
        ``copy_context()`` snapshot from the event loop.  A contextvar set
        inside the dep's threadpool call is NOT visible in the endpoint body's
        threadpool call (proved by test_rls_endpoints.py with real TestClient:
        ValueError raised on token reset, and row counts were 0 without the
        fix).  ``session.info`` is a plain dict carried on the Session object
        itself, so it is shared by reference across all threadpool calls that
        hold the same Session.  It survives commits (``after_begin`` re-fires on
        each new transaction and re-reads session.info), and it is discarded
        when the session is closed at request end.

    Fail-closed guarantee:
        Missing or empty ``session.info`` keys default to ``''``.  The RLS
        policy reads ``nullif(current_setting('app.user_id', true), '')::bigint``
        which evaluates to NULL for ``''``, matching no row.

    Pre-wired FastAPI dependency helpers exported from this module:
        ``get_db_for_principal`` — depends on ``get_principal``; use on all
            bot/user-facing routes.
        ``get_db_for_admin`` — depends on ``require_admin``; use on admin
            catalog routes.

Event choice — ``Session.after_begin``:
    ``after_begin`` fires after SQLAlchemy begins a new DBAPI transaction.  It
    receives the live DBAPI connection so we can execute raw SQL without going
    through the ORM.  It fires for both read and write transactions, and it
    re-fires after each commit+new-begin within the same session, so the GUCs
    are always fresh for the current transaction.
"""
import logging
from typing import Generator, Optional

from fastapi import Depends
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings
from app.middleware.permissions import (
    Principal,
    get_current_user,
    get_principal,
    require_admin,
)

logger = logging.getLogger(__name__)

settings = get_settings()

# Runtime engine — connects as app_rw; RLS policies apply.
engine = create_engine(settings.APP_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(SessionLocal, "after_begin")
def _set_rls_gucs(session: Session, transaction: object, connection: object) -> None:
    """Inject per-request RLS GUCs at the start of every transaction.

    Reads ``session.info['app_user_id']`` and ``session.info['app_role']``
    (populated by ``get_db`` from the resolved principal) and emits a
    ``set_config`` call with ``is_local=true`` so the GUC resets automatically
    at transaction end.

    Falls back to ``''`` for any missing key — fail-closed: the RLS policy's
    ``nullif(..., '')::bigint`` evaluates to NULL, matching no row.

    Uses ``session.info`` (not contextvars) so the GUC is always visible to
    the endpoint-body threadpool call regardless of contextvar propagation
    across threads (GYM-37 fix).

    Args:
        session: The SQLAlchemy session that just began a transaction.
        transaction: SQLAlchemy ``SessionTransaction`` object (unused).
        connection: The DBAPI-level connection for this transaction.
    """
    uid = session.info.get("app_user_id", "")
    role = session.info.get("app_role", "")
    logger.debug("after_begin: set_config user_id=%r role=%r", uid, role)
    connection.execute(
        text(
            "SELECT set_config('app.user_id', :uid, true),"
            " set_config('app.role', :role, true)"
        ),
        {"uid": uid, "role": role},
    )


def get_db(principal: Optional[dict] = None) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session with RLS context set from the principal.

    Stashes the resolved principal on ``session.info`` so the ``after_begin``
    event can inject the correct GUC for every transaction the session opens —
    including after mid-request commits.

    When called without a principal both ``app_user_id`` and ``app_role``
    default to ``''``, which is fail-closed (the RLS policy returns 0 rows).

    Args:
        principal: Resolved identity dict with ``user_id`` (int) and
            ``role`` (str), or ``None`` for unauthenticated access.

    Yields:
        An active ``Session`` instance with RLS context populated.
    """
    db = SessionLocal()
    db.info["app_user_id"] = (
        str(principal["user_id"])
        if principal and principal.get("user_id") is not None
        else ""
    )
    db.info["app_role"] = (principal or {}).get("role") or ""
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-wired FastAPI dependency helpers
#
# These thin wrappers expose ``get_db`` as a FastAPI ``Depends``-able dep that
# also resolves the auth principal.  FastAPI deduplicates dependencies by
# identity — if a route also declares ``principal = Depends(get_principal)``,
# it is resolved only ONCE and the same value is passed here.
# ---------------------------------------------------------------------------


def get_db_for_principal(
    principal: Principal = Depends(get_principal),
) -> Generator[Session, None, None]:
    """Yield a session with RLS context for bot/user-facing routes.

    Wraps ``get_db`` with a ``get_principal`` dependency.  Use as
    ``db: Session = Depends(get_db_for_principal)`` on any route that uses
    the service-token or JWT user auth path.

    Args:
        principal: Resolved by ``get_principal`` via FastAPI DI.

    Yields:
        A session with ``session.info`` pre-populated from the principal.
    """
    yield from get_db(principal)


def get_db_for_admin(
    current_user: dict = Depends(require_admin),
) -> Generator[Session, None, None]:
    """Yield a session with RLS context for admin routes.

    Synthesises a minimal principal with ``role='admin'`` from the JWT claims
    so the ``after_begin`` event injects ``app.role='admin'``, allowing the
    admin RLS policy branch to expose all rows.

    Use as ``db: Session = Depends(get_db_for_admin)`` on admin catalog routes
    instead of ``Depends(get_db)`` to ensure the admin GUC is set.

    Args:
        current_user: JWT claims dict from ``require_admin`` via FastAPI DI.

    Yields:
        A session with ``session.info`` set to role='admin'.
    """
    # Admin 'sub' is the string 'admin' — int() raises; user_id stays None.
    try:
        uid: Optional[int] = int(current_user.get("sub", ""))
    except (TypeError, ValueError):
        uid = None
    admin_principal = {"user_id": uid, "role": "admin"}
    yield from get_db(admin_principal)


def get_db_for_user(
    current_user: dict = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """Yield a session with RLS context for legacy user routes.

    Synthesises a principal from the JWT claims (``sub`` as user_id, ``role``
    from token) so the ``after_begin`` event injects the correct GUC for
    legacy ``/user/*`` endpoints.

    Use as ``db: Session = Depends(get_db_for_user)`` on routes that depend
    on ``get_current_user`` or ``require_user``.

    Args:
        current_user: JWT claims dict from ``get_current_user`` via FastAPI DI.

    Yields:
        A session with ``session.info`` pre-populated from the JWT claims.
    """
    try:
        uid: Optional[int] = int(current_user.get("sub", ""))
    except (TypeError, ValueError):
        uid = None
    role = current_user.get("role", "user")
    user_principal = {"user_id": uid, "role": role}
    yield from get_db(user_principal)
