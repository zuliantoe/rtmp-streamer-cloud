import asyncio
import os
import re
import signal
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, List, Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models import PlaylistItem, StreamMode, StreamSession, StreamSourceType, StreamStatus, Video
from .websocket_manager import ws_manager


PROGRESS_REGEX = re.compile(
    r"fps=\s*(?P<fps>[\d\.]+).*?bitrate=\s*(?P<bitrate>\S+)", re.IGNORECASE
)
DROP_REGEX = re.compile(r"drop=\s*(?P<dropped>\d+)", re.IGNORECASE)


@dataclass
class FfmpegStats:
    bitrate: Optional[str] = None
    fps: Optional[str] = None
    dropped_frames: Optional[str] = None


def _build_input_args(db: Session, source_type: StreamSourceType, source_id: int, mode: StreamMode) -> List[str]:
    if source_type == StreamSourceType.video:
        video: Video | None = db.query(Video).filter(Video.id == source_id).first()
        if not video:
            raise ValueError("Video not found")
        loop_arg = []
        if mode == StreamMode.loop_video:
            loop_arg = ["-stream_loop", "-1"]
        return ["-re", *loop_arg, "-i", video.filepath]

    # playlist
    items = (
        db.query(PlaylistItem)
        .filter(PlaylistItem.playlist_id == source_id)
        .order_by(PlaylistItem.order_index.asc())
        .all()
    )
    if not items:
        raise ValueError("Playlist is empty")
    playlist_lines = [f"file '{db.query(Video).get(it.video_id).filepath}'" for it in items]
    temp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    temp.write("\n".join(playlist_lines))
    temp.flush()
    temp.close()
    input_args = ["-re", "-f", "concat", "-safe", "0", "-i", temp.name]
    if mode == StreamMode.loop_playlist:
        # emulate loop by using -stream_loop on concat is unsupported; instead restart on end externally
        pass
    return input_args


async def _read_stream_lines(stream: asyncio.StreamReader) -> AsyncIterator[str]:
    buffer = ""
    while True:
        chunk = await stream.read(1024)
        if not chunk:
            # flush remaining buffer
            if buffer:
                for part in re.split(r"[\r\n]+", buffer):
                    if part:
                        yield part
            break
        buffer += chunk.decode(errors="ignore")
        parts = re.split(r"[\r\n]+", buffer)
        buffer = parts.pop()  # last incomplete
        for part in parts:
            if part:
                yield part


def _parse_stats(line: str) -> FfmpegStats | None:
    match = PROGRESS_REGEX.search(line)
    if not match:
        return None
    dropped = None
    d = DROP_REGEX.search(line)
    if d:
        dropped = d.group("dropped")
    return FfmpegStats(
        bitrate=match.group("bitrate"),
        fps=match.group("fps"),
        dropped_frames=dropped,
    )


async def start_ffmpeg(db: Session, session: StreamSession) -> int:
    input_args = _build_input_args(db, session.source_type, session.source_id, session.mode)

    output_args = [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-b:v",
        "3000k",
        "-maxrate",
        "3000k",
        "-bufsize",
        "6000k",
        "-c:a",
        "aac",
        "-f",
        "flv",
        session.destination,
    ]

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-stats",
        *input_args,
        "-y",
        *output_args,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    session.pid = process.pid
    session.status = StreamStatus.running
    session.start_time = datetime.now(timezone.utc)
    db.commit()

    # send initial status so client can show running immediately
    await ws_manager.broadcast(
        session.id,
        {
            "type": "status",
            "status": session.status.value,
            "rtmp_url": session.destination,
        },
    )

    async def _pump_and_wait():
        last_stats: FfmpegStats | None = None
        async for line in _read_stream_lines(process.stderr):
            stats = _parse_stats(line)
            if stats:
                last_stats = stats
                await ws_manager.broadcast(
                    session.id,
                    {
                        "type": "stats",
                        "bitrate": stats.bitrate,
                        "fps": stats.fps,
                        "dropped_frames": stats.dropped_frames,
                        "rtmp_url": session.destination,
                        "status": session.status.value,
                    },
                )
        # process finished
        await process.wait()
        session.status = StreamStatus.stopped
        session.end_time = datetime.now(timezone.utc)
        if last_stats and last_stats.bitrate:
            session.avg_bitrate = last_stats.bitrate
        db.commit()
        await ws_manager.broadcast(
            session.id,
            {
                "type": "status",
                "status": session.status.value,
                "rtmp_url": session.destination,
                "avg_bitrate": session.avg_bitrate,
            },
        )

    asyncio.create_task(_pump_and_wait())
    return process.pid


def stop_ffmpeg(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


