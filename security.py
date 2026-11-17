from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import SECRET_KEY, TOKEN_MINUTES
from .database import get_db
from .models import User

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
ALGO = "HS256"


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)


def make_token(user: User) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET_KEY, algorithm=ALGO)


def current_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        uid = int(jwt.decode(token, SECRET_KEY, algorithms=[ALGO])["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u:
        raise HTTPException(401, "User not found")
    return u


def require(*roles):
    def dep(u: User = Depends(current_user)) -> User:
        if roles and u.role not in roles:
            raise HTTPException(403, "Not allowed for your role")
        return u
    return dep
