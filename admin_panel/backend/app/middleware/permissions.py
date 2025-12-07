from fastapi import HTTPException, Header
from typing import Optional
from app.core.auth import verify_session_token


def get_current_user(authorization: str = Header(None)):
    """
    Extract and verify user from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User data from JWT
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user_data = verify_session_token(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data


def require_role(required_role: str):
    """
    Dependency to enforce role-based access control.
    
    Args:
        required_role: Required role ("admin" or "user")
        
    Returns:
        User data if authorized
        
    Raises:
        HTTPException: If user doesn't have required role
    """
    def role_checker(authorization: str = Header(None)):
        user = get_current_user(authorization)
        
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {required_role}"
            )
        
        return user
    
    return role_checker


def require_admin(authorization: str = Header(None)):
    """Shorthand for requiring admin role"""
    return require_role("admin")(authorization)


def require_user(authorization: str = Header(None)):
    """Shorthand for requiring user role (any authenticated user)"""
    user = get_current_user(authorization)
    return user
