import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

type Video = { id: number; filename: string; filepath: string }
type Playlist = { id: number; name: string; items: { id: number; video_id: number; order_index: number }[] }

export default function Dashboard() {
  const nav = useNavigate()
  const token = localStorage.getItem('token')
  useEffect(() => { if (!token) nav('/login') }, [token])

  const [videos, setVideos] = useState<Video[]>([])
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [selectedType, setSelectedType] = useState<'video'|'playlist'>('video')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [rtmp, setRtmp] = useState('rtmp://example.com/live/streamkey')
  const [mode, setMode] = useState<'once'|'loop_video'|'loop_playlist'>('once')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [stats, setStats] = useState<any>({})

  const ws = useRef<WebSocket | null>(null)
  const [wsStatus, setWsStatus] = useState<'disconnected'|'connecting'|'connected'>('disconnected')
  const [pingMs, setPingMs] = useState<number | null>(null)
  const pingNonce = useRef<number>(0)
  const pingSentAt = useRef<number>(0)

  async function refresh() {
    const [v, p] = await Promise.all([
      api.get('/api/videos/'),
      api.get('/api/playlists/'),
    ])
    setVideos(v.data)
    setPlaylists(p.data)
  }

  useEffect(() => { refresh() }, [])

  async function onUpload(e: any) {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    await api.post('/api/videos/upload', form)
    await refresh()
  }

  const apiBase = useMemo(() => ((import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000').replace(/\/$/, ''), [])
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
    setSessionId(data.id)
    const url = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
    setWsStatus('connecting')
    ws.current = new WebSocket(url.replace('http', 'ws') + `/ws/streams/${data.id}`)
    ws.current.onopen = () => setWsStatus('connected')
    ws.current.onclose = () => { setWsStatus('disconnected'); setPingMs(null) }
    ws.current.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg?.type === 'pong' && msg?.nonce === pingNonce.current) {
          const now = Date.now()
          const rtt = now - pingSentAt.current
          setPingMs(rtt)
          return
        }
        setStats(msg)
      } catch {}
    }
    // heartbeat
    const interval = setInterval(() => {
      if (ws.current && ws.current.readyState === ws.current.OPEN) {
        pingNonce.current = (pingNonce.current + 1) % 1e9
        pingSentAt.current = Date.now()
        ws.current.send(JSON.stringify({ type: 'ping', nonce: pingNonce.current, client_time: pingSentAt.current }))
      }
    }, 5000)
    // cleanup
    const sock = ws.current
    sock.addEventListener('close', () => clearInterval(interval))
  }

  async function stopStreaming() {
    if (!sessionId) return
    await api.post(`/api/streams/stop/${sessionId}`)
    setSessionId(null)
    ws.current?.close()
  }

  return (
    <div className="p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">CloudRTMP Dashboard</h1>
        <button className="text-sm text-red-600" onClick={() => { localStorage.removeItem('token'); nav('/login') }}>Logout</button>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Upload Video</h2>
            <input type="file" accept="video/mp4" onChange={onUpload} />
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Videos</h2>
            <ul className="space-y-1 max-h-64 overflow-auto">
              {videos.map(v => (
                <li key={v.id} className="flex items-center justify-between">
                  <button className={`text-left ${selectedType==='video'&&selectedId===v.id?'font-semibold':''}`} onClick={() => { setSelectedType('video'); setSelectedId(v.id); setMode('once') }}>{v.filename}</button>
                  <a className="text-blue-600 text-sm" href={toVideoUrl(v.filepath)} target="_blank">preview</a>
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
              <button className="bg-gray-600 text-white px-3 py-1 rounded" onClick={stopStreaming} disabled={!sessionId}>Stop</button>
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Live Stats</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-gray-500">RTMP:</span> {stats.rtmp_url || '-'}</div>
              <div><span className="text-gray-500">Bitrate:</span> {stats.bitrate || '-'}</div>
              <div><span className="text-gray-500">FPS:</span> {stats.fps || '-'}</div>
              <div><span className="text-gray-500">Dropped:</span> {stats.dropped_frames || '-'}</div>
              <div><span className="text-gray-500">Status:</span> {stats.status || (sessionId?'running':'stopped')}</div>
              <div><span className="text-gray-500">WS:</span> {wsStatus}{pingMs!=null?` (${pingMs}ms)`:''}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


