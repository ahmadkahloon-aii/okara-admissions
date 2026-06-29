"""Auth router: login + current user."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import verify_password, create_access_token, get_current_user
from ..schemas import Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username.lower()).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.email)
    return Token(access_token=token, user={"id": user.id, "email": user.email,
                                           "name": user.name, "role": user.role})


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
