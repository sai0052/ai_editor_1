import { useMemo, useRef, useState } from 'react'
import { Check, Download, RotateCcw } from 'lucide-react'
import type { EditSummary, ExportOptions, JobResponse } from '../types'
import { ExportPanel } from './ExportPanel'

interface Props {
  job: JobResponse
  originalUrl: string
  resultUrl: string
  exportOptions: ExportOptions
  onExportChange: (next: ExportOptions) => void
  onRestart: () => void
  onDownload: () => void
}

export function ResultView({
  job,
  originalUrl,
  resultUrl,
  exportOptions,
  onExportChange,
  onRestart,
  onDownload,
}: Props) {
  const [mode, setMode] = useState<'edited' | 'original' | 'side'>('edited')
  const [slider, setSlider] = useState(50)
  const editedRef = useRef<HTMLVideoElement>(null)
  const originalRef = useRef<HTMLVideoElement>(null)

  const bullets = useMemo(() => summaryBullets(job.summary), [job.summary])

  return (
    <section className="result-view">
      <div className="panel result-main">
        <div className="result-toolbar">
          <h2>Preview</h2>
          <div className="seg">
            <button type="button" className={mode === 'edited' ? 'active' : ''} onClick={() => setMode('edited')}>
              Edited
            </button>
            <button type="button" className={mode === 'original' ? 'active' : ''} onClick={() => setMode('original')}>
              Original
            </button>
            <button type="button" className={mode === 'side' ? 'active' : ''} onClick={() => setMode('side')}>
              Compare
            </button>
          </div>
        </div>

        {mode !== 'side' ? (
          <div className="preview-frame tall">
            <video
              key={mode}
              ref={mode === 'edited' ? editedRef : originalRef}
              src={mode === 'edited' ? resultUrl : originalUrl}
              controls
              playsInline
            />
          </div>
        ) : (
          <div className="compare-wrap">
            <div className="compare-side">
              <span>Before</span>
              <video ref={originalRef} src={originalUrl} controls playsInline />
            </div>
            <div className="compare-side">
              <span>After</span>
              <video ref={editedRef} src={resultUrl} controls playsInline />
            </div>
            <div className="slider-compare">
              <label>
                Focus
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={slider}
                  onChange={(e) => setSlider(Number(e.target.value))}
                />
              </label>
              <div className="slider-hint">Use side-by-side players for precise A/B review.</div>
            </div>
          </div>
        )}

        <div className="result-actions">
          <button type="button" className="btn primary lg" onClick={onDownload}>
            <Download size={18} /> Download
          </button>
          <button type="button" className="btn ghost" onClick={onRestart}>
            <RotateCcw size={16} /> Start another edit
          </button>
        </div>
      </div>

      <aside className="result-side">
        <div className="panel">
          <h3>AI edit summary</h3>
          <ul className="summary-list">
            {bullets.map((b) => (
              <li key={b}>
                <Check size={16} /> {b}
              </li>
            ))}
            {!bullets.length && <li>Processing complete.</li>}
          </ul>
          {job.summary?.notes?.map((n) => (
            <p key={n} className="note">
              {n}
            </p>
          ))}
        </div>
        <ExportPanel value={exportOptions} onChange={onExportChange} onExport={onDownload} />
      </aside>
    </section>
  )
}

function summaryBullets(summary?: EditSummary | null): string[] {
  if (!summary) return []
  const out: string[] = []
  if (summary.noise_reduced) out.push('Background noise reduced')
  if (summary.silences_removed) out.push(`${summary.silences_removed} silent sections removed`)
  if (summary.pauses_shortened) out.push(`${summary.pauses_shortened} pauses shortened`)
  if (summary.captions_generated) out.push('Captions generated')
  if (summary.color_applied) out.push('Color grading applied')
  if (summary.filler_removed) out.push(`${summary.filler_removed} filler words removed`)
  if (summary.jump_cuts) out.push(`${summary.jump_cuts} jump cuts applied`)
  if (summary.reframed) out.push('Video reframed')
  return out
}
