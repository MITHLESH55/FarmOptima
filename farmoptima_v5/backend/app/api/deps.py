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


def get_authorized_recommendation(recommendation_id: int, current_user: User, db: Session):
    """
    Retrieves a recommendation and enforces ownership.
    Returns 404 (RecommendationNotFoundError) if it does not exist OR belongs to another user
    to prevent revealing the existence of other users' recommendations.
    """
    from app.models import Recommendation, Farm
    from app.utils.exceptions import RecommendationNotFoundError

    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found.")

    farm = db.query(Farm).filter(Farm.id == rec.farm_id).first()
    if not farm or farm.user_id != current_user.id:
        raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found.")

    return rec
