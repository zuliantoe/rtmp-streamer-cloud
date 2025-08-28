## CloudRTMP

CloudRTMP adalah aplikasi web untuk mengelola video (upload/playlist) dan melakukan streaming ke RTMP server menggunakan ffmpeg. Backend menggunakan FastAPI + PostgreSQL (SQLAlchemy + Alembic), frontend menggunakan React + Vite + Tailwind. Realtime stats (bitrate, fps, dropped frames) dikirim via WebSocket dari parsing log ffmpeg.

### Arsitektur Singkat
- Backend: FastAPI (Python 3.11)
- DB: PostgreSQL, ORM: SQLAlchemy, Migrasi: Alembic
- Frontend: React + Vite + Tailwind
- Streaming: ffmpeg dijalankan via subprocess, push stats via WebSocket
- Auth: JWT (bearer), password bcrypt, role: admin/user

### Fitur
- User: Register/Login/Logout (JWT)
- Video: Upload/Hapus/List (+preview via static `/videos`)
- Playlist: Buat, tambah video, reorder
- Streaming: pilih sumber (video/playlist), mode (once/loop), RTMP dest, start/stop, status
- Realtime Stats: bitrate, fps, dropped frames, rtmp url via WS `/ws/streams/{session_id}`
- History/Logs: tersimpan di tabel `logs` dan `stream_sessions`

### Prasyarat
- Docker & Docker Compose

### Jalankan dengan Docker Compose
```bash
docker compose up --build
```

Layanan:
- API: http://localhost:8000 (FastAPI)
- Frontend: http://localhost:5173

Folder video di-mount ke volume `videos` dan disajikan oleh backend di path `/videos` untuk preview.

### Konfigurasi Lingkungan
Lihat `.env.example` untuk variabel yang tersedia. Environment utama:
- `SECRET_KEY` (ubah di produksi)
- `DATABASE_URL` (default mengarah ke service `db` di compose)
- `VIDEOS_DIR` (default `/videos`)
- `CORS_ORIGINS` (default `*`)

### Migrasi Database
Alembic sudah disiapkan dengan revisi awal.
Menjalankan migrasi (dalam container backend):
```bash
docker compose exec backend bash -lc "alembic upgrade head"
```

### Menjalankan Lokal (tanpa Docker)
1. Setup Python env, install requirements:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST:5432/cloud_rtmp
export VIDEOS_DIR=$(pwd)/videos
uvicorn uvicorn_app:app --reload
```
2. Frontend:
```bash
cd frontend
npm install
npm run dev
```

### API Ringkas
- Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- Videos: `GET /api/videos/`, `POST /api/videos/upload`, `DELETE /api/videos/{id}`
- Playlists: `GET /api/playlists/`, `POST /api/playlists/`, tambah item `POST /api/{playlist_id}/items/{video_id}`, `POST /api/{playlist_id}/reorder`, `DELETE /api/playlists/{playlist_id}`
- Streams: `POST /api/streams/start`, `POST /api/streams/stop/{id}`, `GET /api/streams/status/{id}`
- WS: `ws://<backend>/ws/streams/{session_id}` (stats json)

### Catatan Streaming
- Mode loop playlist tingkat lanjut (restart otomatis di akhir) dapat ditambahkan di runner dengan memantau exit code dan me-restart proses.
- ffmpeg harus tersedia (di Dockerfile sudah terpasang).

### Deployment
- VPS Ubuntu 22.04: install Docker + docker compose plugin, clone repo ini, `docker compose up -d --build`.
- Reverse proxy (opsional) dengan Nginx untuk domain dan TLS.

### Lisensi
MIT
web base rtmp streamer
