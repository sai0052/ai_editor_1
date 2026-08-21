import type { EditOptions, ExportOptions, JobResponse, VideoMetadata } from '../types'

const API = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || '/api'

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    return data.error || data.detail || 'Request failed'
  } catch {
    return `Request failed (${res.status})`
  }
}

export async function uploadVideo(file: File): Promise<{ video_id: string; metadata: VideoMetadata }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/videos/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function createJob(
  videoId: string,
  options: EditOptions,
  exportOptions: ExportOptions,
): Promise<JobResponse> {
  const res = await fetch(`${API}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, options, export: exportOptions }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${API}/jobs/${jobId}`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export function videoFileUrl(videoId: string): string {
  return `${API}/videos/${videoId}/file`
}

export function jobResultUrl(jobId: string): string {
  return `${API}/jobs/${jobId}/result`
}
