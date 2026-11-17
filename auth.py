from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..security import verify_password, make_token, current_user, require, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _me(u: User):
    return dict(id=u.id, username=u.username, role=u.role, full_name=u.full_name,
                faculty_id=u.faculty_id, student_id=u.student_id)


@router.post("/token")                       # OAuth2 form (Swagger "Authorize" button)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return _login(form.username, form.password, db)


class Login(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: Login, db: Session = Depends(get_db)):
    return _login(body.username, body.password, db)


def _login(username, password, db):
    u = db.query(User).filter(User.username == username.strip().lower()).first()
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(401, "Invalid username or password")
    return dict(access_token=make_token(u), token_type="bearer", user=_me(u))


@router.get("/me")
def me(u: User = Depends(current_user)):
    return _me(u)


class Change(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
def change(body: Change, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, u.password_hash):
        raise HTTPException(400, "Old password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    u.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


class Reset(BaseModel):
    username: str
    new_password: str = "Giet@123"


@router.post("/reset-password")             # admin resets a forgotten password
def reset(body: Reset, _: User = Depends(require("admin")), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == body.username.strip().lower()).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "username": u.username}
