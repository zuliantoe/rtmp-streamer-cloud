import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import StreamSession, StreamStatus, User, UserRole
from ..schemas import StreamStartRequest, StreamStatusOut
from ..services.websocket_manager import ws_manager
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
        status=StreamStatus.running,
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


@router.get("/active", response_model=List[StreamStatusOut])
def list_active_streams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(StreamSession).filter(StreamSession.status == StreamStatus.running)
    if current_user.role != UserRole.admin:
        query = query.filter(StreamSession.user_id == current_user.id)
    sessions = query.order_by(StreamSession.start_time.desc()).all()
    # enrich with last stats via response_model (pydantic will ignore extras)
    for s in sessions:
        _ = ws_manager.get_last_stats(s.id)
    return sessions


