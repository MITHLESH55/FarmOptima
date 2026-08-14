from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import FarmOut, LocationRequest
from app.models import Farm, User
from app.api.deps import get_current_user

router = APIRouter(prefix="/farms", tags=["farms"])


@router.get("", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Farm).order_by(Farm.created_at.desc()).all()


@router.post("", response_model=FarmOut)
def create_farm(
    loc: LocationRequest, name: str | None = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    farm = Farm(name=name, latitude=loc.lat, longitude=loc.lon)
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm
