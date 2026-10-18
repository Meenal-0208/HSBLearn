"""
HSBLearn Server-Side Authentication & Session Management.
Uses salted SHA-256 for predictable fast local prototype verification
and signed JWT tokens via python-jose.
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, jwt
from backend.database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "hsblearn-secure-prototype-secret-key-32chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
SALT = "hsblearn_salt_"

def get_password_hash(password: str) -> str:
    return hashlib.sha256(f"{SALT}{password}".encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Validates Bearer token and returns authenticated user dict.
    Raises 401 if unauthenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub_val = payload.get("sub")
        if sub_val is None:
            raise credentials_exception
        user_id = int(sub_val)
    except Exception:
        raise credentials_exception

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise credentials_exception
        return dict(user)
