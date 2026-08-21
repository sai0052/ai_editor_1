import type { ExportOptions } from '../types'

interface Props {
  value: ExportOptions
  onChange: (next: ExportOptions) => void
  onExport: () => void
}

export function ExportPanel({ value, onChange, onExport }: Props) {
  return (
    <div className="panel export-panel">
      <h3>Export settings</h3>
      <label className="field">
        <span>Resolution</span>
        <select
          value={value.resolution}
          onChange={(e) => onChange({ ...value, resolution: e.target.value as ExportOptions['resolution'] })}
        >
          <option value="original">Original</option>
          <option value="1080p">1080p</option>
          <option value="720p">720p</option>
        </select>
      </label>
      <label className="field">
        <span>Format</span>
        <select value={value.format} disabled>
          <option value="mp4">MP4</option>
        </select>
      </label>
      <label className="field">
        <span>FPS</span>
        <select
          value={value.fps}
          onChange={(e) => onChange({ ...value, fps: e.target.value as ExportOptions['fps'] })}
        >
          <option value="original">Original</option>
          <option value="24">24</option>
          <option value="30">30</option>
          <option value="60">60</option>
        </select>
      </label>
      <label className="field">
        <span>Quality</span>
        <select
          value={value.quality}
          onChange={(e) => onChange({ ...value, quality: e.target.value as ExportOptions['quality'] })}
        >
          <option value="standard">Standard</option>
          <option value="high">High</option>
          <option value="maximum">Maximum</option>
        </select>
      </label>
      <button type="button" className="btn primary block" onClick={onExport}>
        Export video
      </button>
      <p className="hint">Current download uses the rendered master. Re-export with new settings is coming next.</p>
    </div>
  )
}
