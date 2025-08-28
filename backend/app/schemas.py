from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from .models import StreamMode, StreamSourceType, StreamStatus, UserRole


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class VideoOut(BaseModel):
    id: int
    filename: str
    filepath: str
    uploaded_by: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class PlaylistItemOut(BaseModel):
    id: int
    video_id: int
    order_index: int

    class Config:
        orm_mode = True


class PlaylistCreate(BaseModel):
    name: str


class PlaylistOut(BaseModel):
    id: int
    name: str
    user_id: int
    items: List[PlaylistItemOut] = []
    created_at: datetime

    class Config:
        orm_mode = True


class StreamStartRequest(BaseModel):
    source_type: StreamSourceType
    source_id: int
    destination: str
    mode: StreamMode


class StreamStatusOut(BaseModel):
    id: int
    status: StreamStatus
    pid: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    avg_bitrate: Optional[str]

    class Config:
        orm_mode = True


class LogOut(BaseModel):
    id: int
    action: str
    details: Optional[str]
    timestamp: datetime

    class Config:
        orm_mode = True


