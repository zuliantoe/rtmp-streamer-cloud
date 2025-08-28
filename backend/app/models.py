from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class StreamStatus(str, Enum):
    running = "running"
    stopped = "stopped"


class StreamSourceType(str, Enum):
    video = "video"
    playlist = "playlist"


class StreamMode(str, Enum):
    once = "once"
    loop_video = "loop_video"
    loop_playlist = "loop_playlist"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    videos = relationship("Video", back_populates="uploader", cascade="all,delete")
    playlists = relationship("Playlist", back_populates="owner", cascade="all,delete")
    stream_sessions = relationship("StreamSession", back_populates="user")
    logs = relationship("Log", back_populates="user")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(1024), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    uploader = relationship("User", back_populates="videos")


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="playlists")
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all,delete")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (
        UniqueConstraint("playlist_id", "order_index", name="uq_playlist_order"),
    )

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False)

    playlist = relationship("Playlist", back_populates="items")
    video = relationship("Video")


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    source_type = Column(SAEnum(StreamSourceType), nullable=False)
    source_id = Column(Integer, nullable=False)
    destination = Column(String(1024), nullable=False)
    mode = Column(SAEnum(StreamMode), nullable=False)
    status = Column(SAEnum(StreamStatus), nullable=False, default=StreamStatus.stopped)
    pid = Column(Integer, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    avg_bitrate = Column(String(50), nullable=True)

    user = relationship("User", back_populates="stream_sessions")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="logs")


