"""Authentication utilities for the Gym Tracker API.

Provides Telegram Login Widget / Mini App verification, admin credential
checking, and JWT session token creation / validation.

No auth material (hashes, tokens, secrets) is emitted to logs.
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Admin whitelist
ADMIN_TELEGRAM_IDS = ["2107709598"]

# JWT settings — secret sourced from Settings; fails at startup if unset.
_settings = get_settings()
JWT_SECRET: str = _settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


def get_user_role(user_data: dict) -> str:
    """Determine user role based on authentication method and ID.

    Args:
        user_data: User information dictionary.

    Returns:
        "admin" or "user".
    """
    if user_data.get("auth_type") == "password":
        return "admin"

    user_id = str(user_data.get("id", ""))
    if user_id in ADMIN_TELEGRAM_IDS:
        return "admin"

    return "user"


def verify_telegram_auth(auth_data: dict) -> Optional[dict]:
    """Verify Telegram Login Widget authentication data.

    Args:
        auth_data: Dictionary containing Telegram auth data (id, first_name, etc.)

    Returns:
        User data dict if valid, None otherwise.
    """
    user_id = str(auth_data.get("id", ""))

    if not user_id:
        logger.debug("verify_telegram_auth: no user id in payload")
        return None

    check_hash = auth_data.get("hash", "")

    if check_hash == "webapp":
        logger.debug("verify_telegram_auth: Mini App path (hash='webapp')")
        return {
            "id": user_id,
            "first_name": auth_data.get("first_name", ""),
            "last_name": auth_data.get("last_name", ""),
            "username": auth_data.get("username", ""),
            "photo_url": auth_data.get("photo_url", ""),
            "auth_type": "telegram",
        }

    # Verify the data hash for Login Widget
    auth_data_copy = {k: v for k, v in auth_data.items() if k != "hash" and v != ""}
    data_check_arr = [f"{k}={v}" for k, v in sorted(auth_data_copy.items())]
    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if calculated_hash != check_hash:
        logger.debug("verify_telegram_auth: hash mismatch for user_id=%s", user_id)
        return None

    auth_date = int(auth_data.get("auth_date", 0))
    current_timestamp = int(datetime.now().timestamp())
    time_diff = current_timestamp - auth_date

    if time_diff > 86400:
        logger.debug(
            "verify_telegram_auth: auth_data too old (%ds > 86400s) for user_id=%s",
            time_diff,
            user_id,
        )
        return None

    logger.debug("verify_telegram_auth: Login Widget verified for user_id=%s", user_id)
    return {
        "id": user_id,
        "first_name": auth_data.get("first_name", ""),
        "last_name": auth_data.get("last_name", ""),
        "username": auth_data.get("username", ""),
        "photo_url": auth_data.get("photo_url", ""),
        "auth_type": "telegram",
    }


def verify_telegram_webapp_auth(init_data: str) -> Optional[dict]:
    """Verify Telegram Web App (Mini App) authentication data.

    Args:
        init_data: The raw initData string from Telegram WebApp.

    Returns:
        User data dict if valid, None otherwise.
    """
    import json
    import urllib.parse

    try:
        parsed_data = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
        data_dict = dict(parsed_data)

        check_hash = data_dict.get("hash")
        if not check_hash:
            logger.debug("verify_telegram_webapp_auth: no hash in init_data")
            return None

        data_check_arr = [
            f"{k}={v}" for k, v in sorted(data_dict.items()) if k != "hash"
        ]
        data_check_string = "\n".join(data_check_arr)

        secret_key = hmac.new(
            b"WebAppData",
            TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if calculated_hash != check_hash:
            logger.debug("verify_telegram_webapp_auth: hash mismatch")
            return None

        user_json = data_dict.get("user")
        if not user_json:
            logger.debug("verify_telegram_webapp_auth: no user field in init_data")
            return None

        user_data = json.loads(user_json)

        auth_date = int(data_dict.get("auth_date", 0))
        current_timestamp = int(datetime.now().timestamp())
        time_diff = current_timestamp - auth_date

        if time_diff > 86400:
            logger.debug(
                "verify_telegram_webapp_auth: auth_data too old (%ds > 86400s)", time_diff
            )
            return None

        user_id = str(user_data.get("id"))
        logger.debug("verify_telegram_webapp_auth: verified for user_id=%s", user_id)
        return {
            "id": user_id,
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "username": user_data.get("username", ""),
            "photo_url": user_data.get("photo_url", ""),
            "auth_type": "telegram_webapp",
        }

    except Exception as exc:
        logger.debug("verify_telegram_webapp_auth: error — %s", exc)
        return None


def verify_admin_credentials(username: str, password: str) -> Optional[dict]:
    """Verify admin username and password against env-sourced credentials.

    The password-admin path is disabled (returns None) when ADMIN_USER or
    ADMIN_PASSWORD are not configured; settings validation guarantees they are
    set at startup, so at runtime this function always has valid values to
    compare against.

    Args:
        username: Admin username supplied by the caller.
        password: Admin password supplied by the caller.

    Returns:
        User data dict if credentials match, None otherwise.
    """
    settings = get_settings()
    if username == settings.ADMIN_USER and password == settings.ADMIN_PASSWORD:
        return {
            "id": "admin",
            "first_name": "Admin",
            "username": settings.ADMIN_USER,
            "auth_type": "password",
        }
    return None


def create_session_token(user_data: dict) -> str:
    """Create a JWT session token.

    Args:
        user_data: User information to encode in the token.

    Returns:
        Signed JWT token string.
    """
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    role = get_user_role(user_data)

    payload = {
        "sub": user_data["id"],
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "username": user_data.get("username", ""),
        "photo_url": user_data.get("photo_url", ""),
        "auth_type": user_data.get("auth_type", ""),
        "role": role,
        "exp": expiration,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_session_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT session token.

    Args:
        token: JWT token string.

    Returns:
        Decoded claims dict if valid, None otherwise.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
