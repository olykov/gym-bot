"""Per-request DB principal context — used by GYM-36 test fixtures only.

NOTE (GYM-37): The production API no longer uses these contextvars to inject
RLS GUCs.  The ``after_begin`` event in ``app.core.database`` now reads from
``session.info`` (populated by ``get_db``), which is shared by reference
across threadpool calls and avoids the contextvar-propagation issue.

These symbols are kept because ``tests/conftest.py`` uses them for the direct
DB session tests (GYM-36 ``rls_session``), where there is no FastAPI threadpool
hop and contextvar-based wiring works correctly.

Design:
- Both vars default to the empty string ``''``.  The RLS policy uses
  ``nullif(current_setting('app.user_id', true), '')::bigint``, so an unset /
  empty GUC produces NULL which matches no row → fail-closed.
- ``set_principal_context`` returns the reset tokens so callers can restore
  the previous state in a ``finally`` block.
"""
import contextvars
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# GUC values (text) for the current request.
# Empty string → RLS treats as unset → 0 rows visible (fail-closed).
current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user_id", default=""
)
current_role: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_role", default=""
)


def set_principal_context(
    user_id: Optional[int],
    role: Optional[str],
) -> Tuple[contextvars.Token, contextvars.Token]:
    """Set per-request GUC context from a resolved principal.

    Must be paired with ``reset_principal_context`` in a ``finally`` block so
    that pooled threads never inherit a stale principal from a prior request.

    Args:
        user_id: Telegram user id.  ``None`` leaves the contextvar at ``''``
            (fail-closed: the GUC will be set to empty string).
        role: ``'user'`` or ``'admin'``.  ``None`` → empty string.

    Returns:
        A tuple ``(uid_token, role_token)`` that can be passed to
        ``reset_principal_context`` to restore the previous state.
    """
    uid_str = str(user_id) if user_id is not None else ""
    role_str = role if role is not None else ""
    uid_token = current_user_id.set(uid_str)
    role_token = current_role.set(role_str)
    logger.debug("db_context: set user_id=%s role=%s", uid_str, role_str)
    return uid_token, role_token


def reset_principal_context(
    uid_token: contextvars.Token,
    role_token: contextvars.Token,
) -> None:
    """Restore the previous GUC context using tokens from ``set_principal_context``.

    Args:
        uid_token: Reset token for ``current_user_id``.
        role_token: Reset token for ``current_role``.
    """
    current_user_id.reset(uid_token)
    current_role.reset(role_token)
    logger.debug("db_context: reset to previous context")
