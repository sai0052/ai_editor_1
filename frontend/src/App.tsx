import { useCallback, useEffect, useMemo, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { Sidebar, type NavId } from './components/Sidebar'
import { UploadZone } from './components/UploadZone'
import { VideoInfo } from './components/VideoInfo'
import { FeatureDashboard } from './components/FeatureDashboard'
import { ProcessingScreen } from './components/ProcessingScreen'
import { ResultView } from './components/ResultView'
import { createJob, jobResultUrl, uploadVideo, videoFileUrl } from './services/api'
import { useJobPolling } from './hooks/useJobPolling'
import { defaultExport, defaultOptions, type EditOptions, type ExportOptions, type VideoMetadata } from './types'
import './App.css'

type Phase = 'idle' | 'uploaded' | 'processing' | 'done'

export default function App() {
  const [nav, setNav] = useState<NavId>('new')
  const [phase, setPhase] = useState<Phase>('idle')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [videoId, setVideoId] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null)
  const [options, setOptions] = useState<EditOptions>(defaultOptions)
  const [exportOptions, setExportOptions] = useState<ExportOptions>(defaultExport)
  const [jobId, setJobId] = useState<string | null>(null)

  const { job, error: pollError } = useJobPolling(phase === 'processing' || phase === 'done' ? jobId : null)

  const originalUrl = useMemo(() => (videoId ? videoFileUrl(videoId) : ''), [videoId])
  const resultUrl = useMemo(() => (jobId ? jobResultUrl(jobId) : ''), [jobId])

  useEffect(() => {
    if (!job || phase !== 'processing') return
    if (job.status === 'completed') setPhase('done')
    if (job.status === 'failed') {
      setError(job.error || 'Processing failed')
      setPhase('done')
    }
  }, [job, phase])

  const onFile = useCallback(async (file: File) => {
    setError(null)
    setUploading(true)
    try {
      const res = await uploadVideo(file)
      setVideoId(res.video_id)
      setMetadata(res.metadata)
      setPhase('uploaded')
      setNav('new')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  const onAutoEdit = async () => {
    if (!videoId) return
    setError(null)
    try {
      const jobRes = await createJob(videoId, options, exportOptions)
      setJobId(jobRes.job_id)
      setPhase('processing')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start editing')
    }
  }

  const restart = () => {
    setPhase('idle')
    setVideoId(null)
    setMetadata(null)
    setJobId(null)
    setOptions(defaultOptions())
    setExportOptions(defaultExport())
    setError(null)
  }

  const anyEnabled = Object.values(options).some((o) => 'enabled' in o && o.enabled)

  return (
    <div className="app-shell">
      <Sidebar
        active={nav}
        onNavigate={(id) => {
          setNav(id)
          if (id === 'new' && phase === 'idle') return
        }}
      />

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{navLabel(nav)}</h1>
            <p className="sub">Professional automatic editing — no timeline required.</p>
          </div>
        </header>

        {(error || pollError) && <div className="error-banner">{error || pollError}</div>}

        {nav === 'dashboard' && (
          <section className="panel empty-state">
            <h2>Welcome to AutoCut</h2>
            <p>Start a new edit to upload a video and let AI handle the tedious parts.</p>
            <button type="button" className="btn primary" onClick={() => setNav('new')}>
              New Edit
            </button>
          </section>
        )}

        {(nav === 'projects' || nav === 'history' || nav === 'settings') && (
          <section className="panel empty-state">
            <h2>{navLabel(nav)}</h2>
            <p>Scaffolded for future project history, accounts, and preferences.</p>
          </section>
        )}

        {nav === 'new' && (
          <>
            {phase === 'idle' && <UploadZone busy={uploading} onFile={onFile} />}

            {phase === 'uploaded' && metadata && videoId && (
              <>
                <VideoInfo metadata={metadata} src={originalUrl} />
                <FeatureDashboard options={options} onChange={setOptions} />
                <div className="auto-edit-bar">
                  <div>
                    <strong>Ready when you are</strong>
                    <p>AutoCut will run only the operations you enabled.</p>
                  </div>
                  <button
                    type="button"
                    className="btn primary lg"
                    disabled={!anyEnabled}
                    onClick={onAutoEdit}
                  >
                    <Sparkles size={18} /> Auto Edit
                  </button>
                </div>
              </>
            )}

            {phase === 'processing' && job && <ProcessingScreen job={job} />}
            {phase === 'processing' && !job && (
              <section className="panel processing">
                <h1>Starting AI editor…</h1>
              </section>
            )}

            {phase === 'done' && job && job.status === 'completed' && videoId && jobId && (
              <ResultView
                job={job}
                originalUrl={originalUrl}
                resultUrl={resultUrl}
                exportOptions={exportOptions}
                onExportChange={setExportOptions}
                onRestart={restart}
                onDownload={() => {
                  const a = document.createElement('a')
                  a.href = resultUrl
                  a.download = 'autocut-export.mp4'
                  a.click()
                }}
              />
            )}

            {phase === 'done' && job?.status === 'failed' && (
              <section className="panel empty-state">
                <h2>Editing failed</h2>
                <p>{job.error}</p>
                <button type="button" className="btn primary" onClick={() => setPhase('uploaded')}>
                  Back to options
                </button>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function navLabel(id: NavId): string {
  switch (id) {
    case 'dashboard':
      return 'Dashboard'
    case 'new':
      return 'New Edit'
    case 'projects':
      return 'Projects'
    case 'history':
      return 'History'
    case 'settings':
      return 'Settings'
  }
}
