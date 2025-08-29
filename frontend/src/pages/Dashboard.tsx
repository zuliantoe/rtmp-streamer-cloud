import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { API_BASE } from '../lib/api'

type Video = { id: number; filename: string; filepath: string }
type Playlist = { id: number; name: string; items: { id: number; video_id: number; order_index: number }[] }

export default function Dashboard() {
  const nav = useNavigate()
  const token = localStorage.getItem('token')
  useEffect(() => { if (!token) nav('/login') }, [token])

  const [videos, setVideos] = useState<Video[]>([])
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadPct, setUploadPct] = useState<number>(0)
  const [selectedType, setSelectedType] = useState<'video'|'playlist'>('video')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [rtmp, setRtmp] = useState('rtmp://example.com/live/streamkey')
  const [mode, setMode] = useState<'once'|'loop_video'|'loop_playlist'>('once')
  // Multi-attach state: sessionId -> { wsStatus, pingMs, stats }
  const [attached, setAttached] = useState<Record<number, { wsStatus: 'disconnected'|'connecting'|'connected', pingMs: number | null, stats: any }>>({})
  const [active, setActive] = useState<any[]>([])

  const socketsRef = useRef<Record<number, { ws: WebSocket, pingNonce: number, pingSentAt: number, interval?: number }>>({})
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  

  async function refresh() {
    const [v, p] = await Promise.all([
      api.get('/api/videos/'),
      api.get('/api/playlists/'),
    ])
    setVideos(v.data)
    setPlaylists(p.data)
  }

  useEffect(() => { refresh(); refreshActive() }, [])
  // restore attachments after reload
  useEffect(() => {
    try {
      const raw = localStorage.getItem('attached_session_ids')
      if (!raw) return
      const ids: number[] = JSON.parse(raw)
      ids.forEach(id => attachSession(id))
    } catch {}
  }, [])

  async function refreshActive() {
    try {
      const { data } = await api.get('/api/streams/active')
      setActive(data)
    } catch {}
  }

  async function onUpload(e: any) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/api/videos/upload', form, {
        onUploadProgress: (e) => {
          if (e.total) setUploadPct(Math.round((e.loaded / e.total) * 100))
        }
      })
      await refresh()
    } finally {
      setUploading(false)
      setUploadPct(0)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const apiBase = useMemo(() => (API_BASE || '').replace(/\/$/, ''), [])
  function toVideoUrl(fp: string) {
    const idx = fp.indexOf('/videos/')
    const path = idx >= 0 ? fp.substring(idx) : `/videos/${fp.split('/').pop()}`
    return apiBase + path
  }
  const previewUrl = useMemo(() => {
    if (selectedType === 'video') {
      const v = videos.find(v => v.id === selectedId)
      return v ? toVideoUrl(v.filepath) : ''
    }
    return ''
  }, [selectedType, selectedId, videos])

  async function startStreaming() {
    if (!selectedId) return
    const { data } = await api.post('/api/streams/start', {
      source_type: selectedType,
      source_id: selectedId,
      destination: rtmp,
      mode,
    })
    attachSession(data.id)
    refreshActive()
  }

  function persistAttachedIds(ids: number[]) {
    localStorage.setItem('attached_session_ids', JSON.stringify(ids))
  }

  function attachSession(id: number) {
    if (socketsRef.current[id]) return
    const wsBase = API_BASE.replace('http', 'ws')
    const ws = new WebSocket(wsBase + `/ws/streams/${id}`)
    socketsRef.current[id] = { ws, pingNonce: 0, pingSentAt: 0 }
    setAttached(prev => ({ ...prev, [id]: { wsStatus: 'connecting', pingMs: null, stats: {} } }))
    ws.onopen = () => {
      setAttached(prev => ({ ...prev, [id]: { ...prev[id], wsStatus: 'connected' } }))
    }
    ws.onclose = () => {
      setAttached(prev => ({ ...prev, [id]: { ...prev[id], wsStatus: 'disconnected', pingMs: null } }))
      const r = socketsRef.current[id]
      if (r?.interval) clearInterval(r.interval)
    }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg?.type === 'pong') {
          const now = Date.now()
          const rtt = now - (socketsRef.current[id]?.pingSentAt || now)
          setAttached(prev => ({ ...prev, [id]: { ...prev[id], pingMs: rtt } }))
          return
        }
        setAttached(prev => ({ ...prev, [id]: { ...prev[id], stats: msg } }))
      } catch {}
    }
    const interval = window.setInterval(() => {
      const rec = socketsRef.current[id]
      if (!rec) return
      if (rec.ws.readyState === rec.ws.OPEN) {
        rec.pingNonce = (rec.pingNonce + 1) % 1e9
        rec.pingSentAt = Date.now()
        rec.ws.send(JSON.stringify({ type: 'ping', nonce: rec.pingNonce, client_time: rec.pingSentAt }))
      }
    }, 5000)
    socketsRef.current[id].interval = interval
    const ids = Object.keys(socketsRef.current).map(k => Number(k))
    persistAttachedIds(ids)
  }

  function detachSession(id: number) {
    const rec = socketsRef.current[id]
    if (rec) {
      try { rec.ws.close() } catch {}
      if (rec.interval) clearInterval(rec.interval)
    }
    delete socketsRef.current[id]
    setAttached(prev => {
      const copy = { ...prev }
      delete copy[id]
      return copy
    })
    const ids = Object.keys(socketsRef.current).map(k => Number(k))
    persistAttachedIds(ids)
  }

  async function stopAndDetach(id: number) {
    await api.post(`/api/streams/stop/${id}`)
    detachSession(id)
    refreshActive()
  }

  return (
    <div className="p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">CloudRTMP Dashboard</h1>
        <button className="text-sm text-red-600" onClick={() => { localStorage.removeItem('token'); nav('/login') }}>Logout</button>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="bg-white p-4 rounded shadow space-y-2">
            <h2 className="font-semibold">Upload Video</h2>
            <input ref={fileInputRef} type="file" accept="video/mp4" className="hidden" onChange={onUpload} />
            <button
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-3 py-1.5 rounded disabled:opacity-60"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? `Uploading ${uploadPct}%` : 'Upload MP4'}
            </button>
            <div className="text-xs text-gray-500">Maksimal: file .mp4 (H.264/AAC)</div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Videos</h2>
            <ul className="space-y-1 max-h-64 overflow-auto">
              {videos.map(v => (
                <li key={v.id} className="flex items-center justify-between gap-2">
                  <button className={`flex-1 text-left ${selectedType==='video'&&selectedId===v.id?'font-semibold':''}`} onClick={() => { setSelectedType('video'); setSelectedId(v.id); setMode('once') }}>{v.filename}</button>
                  <a className="text-blue-600 text-sm" href={toVideoUrl(v.filepath)} target="_blank">preview</a>
                  <button className="text-red-600 text-sm" onClick={async ()=>{ await api.delete(`/api/videos/${v.id}`); refresh() }}>delete</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Preview</h2>
            {previewUrl ? (
              <video src={previewUrl} controls className="w-[300px] h-[300px] object-contain rounded mx-auto bg-black" />
            ) : (
              <div className="text-sm text-gray-600">Select a video to preview</div>
            )}
          </div>

          <div className="bg-white p-4 rounded shadow space-y-2">
            <h2 className="font-semibold">Streaming</h2>
            <div className="grid grid-cols-2 gap-2">
              <select className="border rounded px-2 py-1" value={selectedType} onChange={(e) => setSelectedType(e.target.value as any)}>
                <option value="video">Video</option>
                <option value="playlist">Playlist</option>
              </select>
              <input className="border rounded px-2" placeholder="Destination RTMP" value={rtmp} onChange={(e)=>setRtmp(e.target.value)} />
              <select className="border rounded px-2 py-1" value={mode} onChange={(e) => setMode(e.target.value as any)}>
                <option value="once">Single play</option>
                <option value="loop_video">Loop video</option>
                <option value="loop_playlist">Loop playlist</option>
              </select>
              <select className="border rounded px-2 py-1" value={selectedId ?? ''} onChange={(e)=>setSelectedId(Number(e.target.value))}>
                <option value="">Select source</option>
                {(selectedType==='video'?videos:playlists).map((i:any)=>(
                  <option key={i.id} value={i.id}>{selectedType==='video'?i.filename:i.name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button className="bg-green-600 text-white px-3 py-1 rounded" onClick={startStreaming} disabled={!selectedId}>Start</button>
              <button className="bg-gray-400 text-white px-3 py-1 rounded opacity-60 cursor-not-allowed" title="Use Active Streams to stop specific sessions" disabled>Stop</button>
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Attached Streams (Live)</h2>
            {Object.keys(attached).length === 0 && <div className="text-sm text-gray-500">No attachments</div>}
            <div className="grid gap-2">
              {Object.entries(attached).map(([id, info]) => (
                <div key={id} className="border rounded p-2 text-sm">
                  <div className="flex items-center justify-between">
                    <div>#{id} • {info.wsStatus}{info.pingMs!=null?` (${info.pingMs}ms)`:''}</div>
                    <div className="flex gap-2">
                      <button className="text-red-600" onClick={() => stopAndDetach(Number(id))}>Stop</button>
                      <button className="text-gray-700" onClick={() => detachSession(Number(id))}>Detach</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <div><span className="text-gray-500">RTMP:</span> {info.stats?.rtmp_url || '-'}</div>
                    <div><span className="text-gray-500">Bitrate:</span> {info.stats?.bitrate || '-'}</div>
                    <div><span className="text-gray-500">FPS:</span> {info.stats?.fps || '-'}</div>
                    <div><span className="text-gray-500">Dropped:</span> {info.stats?.dropped_frames || '-'}</div>
                    <div><span className="text-gray-500">Status:</span> {info.stats?.status || '-'}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold">Active Streams</h2>
              <button className="text-sm text-blue-600" onClick={refreshActive}>Refresh</button>
            </div>
            <ul className="text-sm space-y-2 max-h-64 overflow-auto">
              {active.length === 0 && <li className="text-gray-500">No active streams</li>}
              {active.map((s:any) => (
                <li key={s.id} className="border rounded p-2">
                  <div className="flex items-center justify-between">
                    <span>#{s.id} • {s.status} • PID {s.pid??'-'}</span>
                    <div className="flex gap-2">
                      {attached[s.id] ? (
                        <button className="text-gray-700" onClick={() => detachSession(s.id)}>Detach</button>
                      ) : (
                        <button className="text-blue-600" onClick={() => attachSession(s.id)}>Attach</button>
                      )}
                      <button className="text-red-600" onClick={() => stopAndDetach(s.id)}>Stop</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1 text-xs text-gray-700">
                    <div><span className="text-gray-500">RTMP:</span> {s.rtmp_url || '-'}</div>
                    <div><span className="text-gray-500">Bitrate:</span> {s.bitrate || s.avg_bitrate || '-'}</div>
                    <div><span className="text-gray-500">FPS:</span> {s.fps || '-'}</div>
                    <div><span className="text-gray-500">Dropped:</span> {s.dropped_frames || '-'}</div>
                    <div><span className="text-gray-500">Start:</span> {s.start_time ? new Date(s.start_time).toLocaleString() : '-'}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}


