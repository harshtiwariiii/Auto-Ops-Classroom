# utils/jwt_handler.py

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Dict, Any, List

# ============================================================
# JWT CONFIG
# ============================================================
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


# ============================================================
# CREATE TOKEN
# ============================================================
def create_access_token(data: dict) -> str:
    """
    Creates a signed JWT access token with expiration.
    """
    to_encode = data.copy()

    # Ensure "sub" is always a string (JWT standard)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ============================================================
# VERIFY / DECODE TOKEN
# ============================================================
def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token.
    Raises 401 if expired or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["sub"] = str(payload.get("sub"))  # Normalize
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")


# ============================================================
# GET CURRENT USER (Dependency)
# ============================================================
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency for authenticated routes.
    Extracts user info from JWT token.
    """
    token = credentials.credentials
    payload = decode_token(token)

    return {
        "user_id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),
    }


# ============================================================
# ROLE VALIDATION (Middleware-like dependency)
# ============================================================
def require_role(roles: List[str]):
    """
    FastAPI dependency for role-based access control.

    Example:
        @app.get("/teacher-only")
        def route(user = Depends(require_role(["teacher"]))):
            ...
    """

    def role_checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_checker
