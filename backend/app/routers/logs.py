from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Log, User
from ..schemas import LogOut


router = APIRouter()


@router.get("/", response_model=List[LogOut])
def list_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Log)
        .filter((Log.user_id == current_user.id) | (Log.user_id.is_(None)))
        .order_by(Log.timestamp.desc())
        .limit(200)
        .all()
    )


