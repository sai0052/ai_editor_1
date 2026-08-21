import type { VideoMetadata } from '../types'

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

function formatDuration(sec: number): string {
  const s = Math.max(0, Math.round(sec))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  if (h) return `${h}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
  return `${m}:${String(r).padStart(2, '0')}`
}

interface Props {
  metadata: VideoMetadata
  src: string
}

export function VideoInfo({ metadata, src }: Props) {
  return (
    <section className="video-info panel">
      <div className="preview-frame">
        <video src={src} controls playsInline preload="metadata" />
      </div>
      <div className="meta-grid">
        <Meta label="Filename" value={metadata.filename} />
        <Meta label="Duration" value={formatDuration(metadata.duration)} />
        <Meta label="Resolution" value={`${metadata.width}×${metadata.height}`} />
        <Meta label="FPS" value={metadata.fps ? metadata.fps.toFixed(2) : '—'} />
        <Meta label="Size" value={formatBytes(metadata.size_bytes)} />
        <Meta label="Audio" value={metadata.has_audio ? 'Yes' : 'No'} />
      </div>
    </section>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong title={value}>{value}</strong>
    </div>
  )
}
