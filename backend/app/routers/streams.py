import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import StreamSession, StreamStatus, User
from ..schemas import StreamStartRequest, StreamStatusOut
from ..services.ffmpeg_runner import start_ffmpeg, stop_ffmpeg


router = APIRouter()


@router.get("/status/{session_id}", response_model=StreamStatusOut)
def get_status(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/start", response_model=StreamStatusOut)
async def start_stream(payload: StreamStartRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = StreamSession(
        user_id=current_user.id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        destination=payload.destination,
        mode=payload.mode,
        status=StreamStatus.stopped,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    await start_ffmpeg(db, session)
    db.refresh(session)
    return session


@router.post("/stop/{session_id}")
def stop_stream(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Not found")
    if session.pid:
        stop_ffmpeg(session.pid)
        session.status = StreamStatus.stopped
        session.pid = None
    db.commit()
    return {"status": "stopped"}


