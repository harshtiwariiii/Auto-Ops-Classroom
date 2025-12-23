# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
from typing import Dict
from pydantic import BaseModel

from utils.database import db
from utils.password_hash import hash_password, verify_password
from utils.jwt_handler import create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["Auth"])

security = HTTPBearer()


# -----------------------------
# Pydantic Models
# -----------------------------
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str
    full_name: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


# -----------------------------
# Helpers
# -----------------------------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    payload = decode_token(credentials.credentials)
    return {
        "user_id": payload["sub"],
        "role": payload.get("role"),
        "username": payload.get("username"),
    }


# -----------------------------
# Auth Routes
# -----------------------------
@router.post("/register")
def register(user: UserRegister):
    conn = db("users.db")
    cur = conn.cursor()

    # Check duplicates
    cur.execute(
        "SELECT 1 FROM users WHERE username=? OR email=?",
        (user.username, user.email),
    )
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email exists")

    if user.role not in ["student", "teacher"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Role must be student or teacher")

    hashed = hash_password(user.password)

    cur.execute(
        """
        INSERT INTO users (username, email, password_hash, role, full_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user.username, user.email, hashed, user.role, user.full_name),
    )

    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    token = create_access_token(
        {"sub": str(user_id), "role": user.role, "username": user.username}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user_id),
        "username": user.username,
        "role": user.role,
    }


@router.post("/login")
def login(user: UserLogin):
    conn = db("users.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id, password_hash, role, username FROM users WHERE username=?",
        (user.username,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, hash_pw, role, username = row

    if not verify_password(user.password, hash_pw):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        {"sub": str(user_id), "role": role, "username": username}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user_id),
        "username": username,
        "role": role,
    }


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    """Return profile of logged-in user"""
    return user
