from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Log, Playlist, PlaylistItem, User, Video
from ..schemas import PlaylistCreate, PlaylistOut


router = APIRouter()


@router.get("/", response_model=List[PlaylistOut])
def list_playlists(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Playlist)
        .filter(Playlist.user_id == current_user.id)
        .order_by(Playlist.created_at.desc())
        .all()
    )


@router.post("/", response_model=PlaylistOut)
def create_playlist(payload: PlaylistCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    playlist = Playlist(name=payload.name, user_id=current_user.id)
    db.add(playlist)
    db.add(Log(user_id=current_user.id, action="create_playlist", details=payload.name))
    db.commit()
    db.refresh(playlist)
    return playlist


@router.post("/{playlist_id}/items/{video_id}", response_model=PlaylistOut)
def add_item(playlist_id: int, video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    max_order = (
        db.query(PlaylistItem.order_index)
        .filter(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.order_index.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 1
    item = PlaylistItem(playlist_id=playlist_id, video_id=video_id, order_index=next_order)
    db.add(item)
    db.commit()
    db.refresh(playlist)
    return playlist


@router.post("/{playlist_id}/reorder")
def reorder_playlist(playlist_id: int, order: List[int], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).all()
    id_to_item = {it.id: it for it in items}
    if set(order) != set(id_to_item.keys()):
        raise HTTPException(status_code=400, detail="Order list mismatch")
    for idx, item_id in enumerate(order, start=1):
        id_to_item[item_id].order_index = idx
    db.commit()
    return {"status": "ok"}


@router.delete("/{playlist_id}")
def delete_playlist(playlist_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(playlist)
    db.commit()
    return {"status": "deleted"}


