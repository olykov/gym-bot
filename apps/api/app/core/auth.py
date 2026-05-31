import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

# Admin whitelist
ADMIN_TELEGRAM_IDS = ["2107709598"]

# Hardcoded admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "olykov"

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


def get_user_role(user_data: dict) -> str:
    """
    Determine user role based on authentication method and ID.
    
    Args:
        user_data: User information dictionary
        
    Returns:
        "admin" or "user"
    """
    # Password login is always admin
    if user_data.get("auth_type") == "password":
        return "admin"
    
    # Check if Telegram user is in admin whitelist
    user_id = str(user_data.get("id", ""))
    if user_id in ADMIN_TELEGRAM_IDS:
        return "admin"
    
    # Default to user role
    return "user"


def verify_telegram_auth(auth_data: dict) -> Optional[dict]:
    """
    Verify Telegram Login Widget authentication data.
    
    Args:
        auth_data: Dictionary containing Telegram auth data (id, first_name, etc.)
        
    Returns:
        User data if valid and whitelisted, None otherwise
    """
    print(f"[AUTH] Received auth_data: {auth_data}")
    
    # Get user ID for validation
    user_id = str(auth_data.get("id", ""))
    print(f"[AUTH] User ID: {user_id}")
    
    if not user_id:
        print("[AUTH] ERROR: No user ID provided")
        return None
    
    # Check if this is from Telegram Mini App (hash will be 'webapp')
    check_hash = auth_data.get("hash", "")
    print(f"[AUTH] Hash value: {check_hash}")
    
    if check_hash == "webapp":
        print("[AUTH] Mini App authentication detected")
        # Mini App authentication - trust the data from Telegram WebApp
        result = {
            "id": user_id,
            "first_name": auth_data.get("first_name", ""),
            "last_name": auth_data.get("last_name", ""),
            "username": auth_data.get("username", ""),
            "photo_url": auth_data.get("photo_url", ""),
            "auth_type": "telegram"
        }
        print(f"[AUTH] Mini App auth successful: {result}")
        return result
    
    # Verify the data hash for Login Widget
    print("[AUTH] Login Widget authentication - verifying hash")
    # Exclude 'hash' and empty values from validation
    auth_data_copy = {k: v for k, v in auth_data.items() if k != "hash" and v != ""}
    
    # Create data check string
    data_check_arr = [f"{k}={v}" for k, v in sorted(auth_data_copy.items())]
    data_check_string = "\n".join(data_check_arr)
    print(f"[AUTH] Data check string: {data_check_string}")
    
    # Create secret key
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"[AUTH] Calculated hash: {calculated_hash}")
    print(f"[AUTH] Received hash: {check_hash}")
    
    # Verify hash matches
    if calculated_hash != check_hash:
        print("[AUTH] ERROR: Hash mismatch - authentication failed")
        return None
    
    print("[AUTH] Hash verified successfully")
    
    # Check auth_date (should be recent, within 24 hours)
    auth_date = int(auth_data.get("auth_date", 0))
    current_timestamp = int(datetime.now().timestamp())
    time_diff = current_timestamp - auth_date
    
    print(f"[AUTH] Auth date: {auth_date}, Current: {current_timestamp}, Diff: {time_diff}s")
    
    if time_diff > 86400:  # 24 hours
        print(f"[AUTH] ERROR: Auth data too old ({time_diff}s > 86400s)")
        return None
    
    result = {
        "id": user_id,
        "first_name": auth_data.get("first_name", ""),
        "last_name": auth_data.get("last_name", ""),
        "username": auth_data.get("username", ""),
        "photo_url": auth_data.get("photo_url", ""),
        "auth_type": "telegram"
    }
    print(f"[AUTH] Login Widget auth successful: {result}")
    return result


def verify_telegram_webapp_auth(init_data: str) -> Optional[dict]:
    """
    Verify Telegram Web App (Mini App) authentication data.
    
    Args:
        init_data: The raw initData string from Telegram WebApp
        
    Returns:
        User data if valid, None otherwise
    """
    import urllib.parse
    import json
    
    print(f"[AUTH] Verifying Web App init_data: {init_data}")
    
    try:
        # Parse query string
        parsed_data = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
        data_dict = dict(parsed_data)
        
        # Extract hash
        check_hash = data_dict.get("hash")
        if not check_hash:
            print("[AUTH] ERROR: No hash found in init_data")
            return None
            
        # Remove hash from data to verify
        data_check_arr = []
        for k, v in sorted(data_dict.items()):
            if k != "hash":
                data_check_arr.append(f"{k}={v}")
                
        data_check_string = "\n".join(data_check_arr)
        print(f"[AUTH] Web App data check string: {data_check_string}")
        
        # Calculate secret key: HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash: HMAC_SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        print(f"[AUTH] Calculated hash: {calculated_hash}")
        print(f"[AUTH] Received hash: {check_hash}")
        
        if calculated_hash != check_hash:
            print("[AUTH] ERROR: Web App hash mismatch")
            return None
            
        # Parse user data
        user_json = data_dict.get("user")
        if not user_json:
            print("[AUTH] ERROR: No user data in init_data")
            return None
            
        user_data = json.loads(user_json)
        
        # Check auth_date
        auth_date = int(data_dict.get("auth_date", 0))
        current_timestamp = int(datetime.now().timestamp())
        time_diff = current_timestamp - auth_date
        
        if time_diff > 86400:
            print(f"[AUTH] ERROR: Auth data too old ({time_diff}s)")
            return None
            
        result = {
            "id": str(user_data.get("id")),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "username": user_data.get("username", ""),
            "photo_url": user_data.get("photo_url", ""),
            "auth_type": "telegram_webapp"
        }
        print(f"[AUTH] Web App auth successful: {result}")
        return result
        
    except Exception as e:
        print(f"[AUTH] ERROR verifying Web App auth: {e}")
        return None


def verify_admin_credentials(username: str, password: str) -> Optional[dict]:
    """
    Verify admin username and password.
    
    Args:
        username: Admin username
        password: Admin password
        
    Returns:
        User data if valid, None otherwise
    """
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return {
            "id": "admin",
            "first_name": "Admin",
            "username": "admin",
            "auth_type": "password"
        }
    return None


def create_session_token(user_data: dict) -> str:
    """
    Create a JWT session token.
    
    Args:
        user_data: User information to encode in token
        
    Returns:
        JWT token string
    """
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Determine user role
    role = get_user_role(user_data)
    
    payload = {
        "sub": user_data["id"],
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "username": user_data.get("username", ""),
        "photo_url": user_data.get("photo_url", ""),
        "auth_type": user_data.get("auth_type", ""),
        "role": role,  # Add role to JWT
        "exp": expiration
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_session_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT session token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded user data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

