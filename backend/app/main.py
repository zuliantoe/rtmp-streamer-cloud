import os
from pathlib import Path

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine
from .models import Base


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    # CORS
    allow_origins = (
        [o.strip() for o in settings.cors_origins.split(",")]
        if settings.cors_origins
        else ["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables if not using Alembic yet (safe no-op if already exist)
    Base.metadata.create_all(bind=engine)

    # Ensure videos directory exists and mount static serving for preview
    Path(settings.videos_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/videos", StaticFiles(directory=str(settings.videos_dir)), name="videos")

    # Routers
    from .routers import auth as auth_router
    from .routers import videos as videos_router
    from .routers import playlists as playlists_router
    from .routers import streams as streams_router
    from .routers import logs as logs_router
    from .routers import ws as ws_router

    app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
    app.include_router(videos_router.router, prefix="/api/videos", tags=["videos"])
    app.include_router(playlists_router.router, prefix="/api/playlists", tags=["playlists"])
    app.include_router(streams_router.router, prefix="/api/streams", tags=["streams"])
    app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])
    app.include_router(ws_router.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    if settings.auto_restart_streams:
        from .database import SessionLocal
        from .models import StreamSession, StreamStatus
        from .services.ffmpeg_runner import start_ffmpeg

        async def restart_running_streams() -> None:
            db = SessionLocal()
            try:
                sessions = db.query(StreamSession).filter(StreamSession.status == StreamStatus.running).all()
                for s in sessions:
                    # reset pid to ensure fresh process
                    s.pid = None
                    db.commit()
                    await start_ffmpeg(db, s)
            finally:
                db.close()

        @app.on_event("startup")
        async def _startup_restart():
            asyncio.create_task(restart_running_streams())

    return app


app = create_app()


