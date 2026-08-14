"""
`get_current_user` is the one dependency every protected route imports.
Centralizing it here (rather than re-checking tokens in each route) means
there's exactly one place that defines what "authenticated" means for this
API.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils.security import decode_access_token
from app.utils.exceptions import FarmOptimaError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class AuthError(FarmOptimaError):
    status_code = 401
    error_code = "not_authenticated"


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if token is None:
        raise AuthError("Missing bearer token. Include 'Authorization: Bearer <token>'.")

    username = decode_access_token(token)
    if username is None:
        raise AuthError("Invalid or expired token.")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive.")

    return user
