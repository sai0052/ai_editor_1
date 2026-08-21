export type NoiseStrength = 'low' | 'medium' | 'high'
export type SilencePreset = 'conservative' | 'balanced' | 'aggressive'
export type CaptionStyle = 'clean' | 'bold' | 'modern' | 'minimal' | 'social' | 'highlighted'
export type ColorPreset =
  | 'natural'
  | 'cinematic'
  | 'warm'
  | 'cool'
  | 'vibrant'
  | 'moody'
  | 'high_contrast'
  | 'auto'

export interface VideoMetadata {
  filename: string
  duration: number
  width: number
  height: number
  fps: number
  size_bytes: number
  has_audio: boolean
  codec?: string | null
  audio_codec?: string | null
}

export interface EditOptions {
  noise: { enabled: boolean; strength: NoiseStrength }
  silence: {
    enabled: boolean
    preset: SilencePreset
    min_silence_ms: number | null
    keep_silence_ms: number | null
  }
  captions: {
    enabled: boolean
    language: string
    style: CaptionStyle
    font: string
    font_size: number
    position: 'bottom' | 'center' | 'top'
    color: string
    background: string
    stroke: string
    highlight_color: string
    burn_in: boolean
  }
  color: {
    enabled: boolean
    preset: ColorPreset
    auto_color: boolean
    brightness: number
    contrast: number
    saturation: number
    highlights: number
    shadows: number
    temperature: number
  }
  pauses: { enabled: boolean; aggressiveness: number }
  reframe: { enabled: boolean; aspect: '16:9' | '9:16' | '1:1' }
  jump_cuts: { enabled: boolean; aggressiveness: number }
  filler: { enabled: boolean; mode: 'keep' | 'remove' | 'review' }
}

export interface ExportOptions {
  resolution: 'original' | '1080p' | '720p'
  format: 'mp4'
  fps: 'original' | '24' | '30' | '60'
  quality: 'standard' | 'high' | 'maximum'
}

export interface StageProgress {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'skipped' | 'failed'
  detail?: string | null
  progress: number
}

export interface EditSummary {
  noise_reduced: boolean
  silences_removed: number
  captions_generated: boolean
  color_applied: boolean
  filler_removed: number
  jump_cuts: number
  reframed: boolean
  pauses_shortened: number
  notes: string[]
}

export interface JobResponse {
  job_id: string
  status: 'queued' | 'analyzing' | 'processing' | 'rendering' | 'completed' | 'failed' | 'cancelled'
  progress: number
  stages: StageProgress[]
  eta_seconds?: number | null
  error?: string | null
  summary?: EditSummary | null
  original_url?: string | null
  result_url?: string | null
  created_at: string
  updated_at: string
  options?: EditOptions | null
}

export const defaultOptions = (): EditOptions => ({
  noise: { enabled: true, strength: 'medium' },
  silence: { enabled: true, preset: 'balanced', min_silence_ms: null, keep_silence_ms: null },
  captions: {
    enabled: false,
    language: 'auto',
    style: 'clean',
    font: 'Arial',
    font_size: 48,
    position: 'bottom',
    color: '#FFFFFF',
    background: '#000000AA',
    stroke: '#000000',
    highlight_color: '#FFD166',
    burn_in: true,
  },
  color: {
    enabled: false,
    preset: 'natural',
    auto_color: false,
    brightness: 0,
    contrast: 1,
    saturation: 1,
    highlights: 0,
    shadows: 0,
    temperature: 0,
  },
  pauses: { enabled: false, aggressiveness: 0.5 },
  reframe: { enabled: false, aspect: '9:16' },
  jump_cuts: { enabled: false, aggressiveness: 0.4 },
  filler: { enabled: false, mode: 'remove' },
})

export const defaultExport = (): ExportOptions => ({
  resolution: 'original',
  format: 'mp4',
  fps: 'original',
  quality: 'standard',
})
