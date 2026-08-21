import { useCallback, useRef, useState } from 'react'
import { Film, Upload } from 'lucide-react'

interface Props {
  busy?: boolean
  onFile: (file: File) => void
}

export function UploadZone({ busy, onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files?.length || busy) return
      onFile(files[0])
    },
    [busy, onFile],
  )

  return (
    <div
      className={`upload-zone ${dragOver ? 'drag' : ''} ${busy ? 'busy' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        handleFiles(e.dataTransfer.files)
      }}
      onClick={() => !busy && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm,video/x-matroska,.mp4,.mov,.mkv,.webm,.avi,.m4v"
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="upload-icon">
        {busy ? <Film className="spin" size={28} /> : <Upload size={28} />}
      </div>
      <h2>{busy ? 'Uploading video…' : 'Drop your video here'}</h2>
      <p>MP4, MOV, MKV, WebM · up to 2 GB</p>
      {!busy && <span className="upload-cta">Browse files</span>}
    </div>
  )
}
