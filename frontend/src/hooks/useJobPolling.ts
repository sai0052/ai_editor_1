import { useEffect, useRef, useState } from 'react'
import { getJob } from '../services/api'
import type { JobResponse } from '../types'

export function useJobPolling(jobId: string | null, intervalMs = 800) {
  const [job, setJob] = useState<JobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const active = useRef(true)

  useEffect(() => {
    active.current = true
    if (!jobId) {
      setJob(null)
      return
    }

    let timer: number | undefined

    const tick = async () => {
      try {
        const data = await getJob(jobId)
        if (!active.current) return
        setJob(data)
        setError(null)
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          return
        }
        timer = window.setTimeout(tick, intervalMs)
      } catch (err) {
        if (!active.current) return
        setError(err instanceof Error ? err.message : 'Failed to fetch job status')
        timer = window.setTimeout(tick, intervalMs * 2)
      }
    }

    tick()
    return () => {
      active.current = false
      if (timer) window.clearTimeout(timer)
    }
  }, [jobId, intervalMs])

  return { job, error }
}
