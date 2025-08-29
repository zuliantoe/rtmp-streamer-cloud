import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user
from ..models import Log, User, Video
from ..schemas import VideoOut


router = APIRouter()


@router.get("/", response_model=List[VideoOut])
def list_videos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Video).order_by(Video.created_at.desc()).all()


@router.post("/upload", response_model=VideoOut)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .mp4 files are allowed")
    target_dir = Path(settings.videos_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    dest_path = target_dir / safe_name
    idx = 1
    while dest_path.exists():
        stem = Path(safe_name).stem
        dest_path = target_dir / f"{stem}_{idx}.mp4"
        idx += 1
    # Stream to disk in chunks to avoid loading entire file into memory
    with open(dest_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    video = Video(filename=dest_path.name, filepath=str(dest_path), uploaded_by=current_user.id)
    db.add(video)
    db.add(Log(user_id=current_user.id, action="upload_video", details=dest_path.name))
    db.commit()
    db.refresh(video)
    return video


@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    try:
        if Path(video.filepath).exists():
            Path(video.filepath).unlink()
    except Exception:
        # Ignore file delete errors; proceed to DB delete
        pass
    db.delete(video)
    db.add(Log(user_id=current_user.id, action="delete_video", details=str(video_id)))
    db.commit()
    return {"status": "deleted"}


