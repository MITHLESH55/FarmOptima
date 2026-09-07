from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, Token
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.exceptions import FarmOptimaError

router = APIRouter(prefix="/auth", tags=["auth"])


class UsernameTakenError(FarmOptimaError):
    status_code = 409
    error_code = "username_taken"


class InvalidCredentialsError(FarmOptimaError):
    status_code = 401
    error_code = "invalid_credentials"


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise UsernameTakenError(f"Username '{payload.username}' is already registered.")

    user = User(username=payload.username, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect username or password.")

    token = create_access_token(subject=user.username)
    return Token(access_token=token)
