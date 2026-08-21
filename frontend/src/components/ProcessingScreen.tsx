import { Check, Circle, Loader2, X } from 'lucide-react'
import type { JobResponse } from '../types'

interface Props {
  job: JobResponse
}

function formatEta(sec?: number | null): string {
  if (sec == null) return 'Calculating…'
  if (sec <= 1) return 'Almost done'
  if (sec < 60) return `~${Math.ceil(sec)}s remaining`
  return `~${Math.ceil(sec / 60)}m remaining`
}

export function ProcessingScreen({ job }: Props) {
  return (
    <section className="processing panel">
      <div className="processing-hero">
        <div className="pulse-ring" />
        <h1>AI editing your video</h1>
        <p>Only the operations you selected are running.</p>
      </div>

      <div className="progress-block">
        <div className="progress-top">
          <span>Progress</span>
          <strong>{Math.round(job.progress)}%</strong>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${Math.min(100, job.progress)}%` }} />
        </div>
        <div className="progress-eta">{formatEta(job.eta_seconds)}</div>
      </div>

      <ul className="stage-list">
        {job.stages.map((stage) => (
          <li key={stage.id} className={`stage ${stage.status}`}>
            <span className="stage-icon">
              {stage.status === 'completed' && <Check size={16} />}
              {stage.status === 'running' && <Loader2 size={16} className="spin" />}
              {stage.status === 'failed' && <X size={16} />}
              {(stage.status === 'pending' || stage.status === 'skipped') && <Circle size={14} />}
            </span>
            <div>
              <div className="stage-label">{stage.label}</div>
              {stage.detail && <div className="stage-detail">{stage.detail}</div>}
            </div>
          </li>
        ))}
      </ul>

      {job.error && <div className="error-banner">{job.error}</div>}
    </section>
  )
}
