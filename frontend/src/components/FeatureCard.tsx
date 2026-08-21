import type { ReactNode } from 'react'

interface Props {
  title: string
  description: string
  icon: ReactNode
  enabled: boolean
  onToggle: (enabled: boolean) => void
  children?: ReactNode
  badge?: string
}

export function FeatureCard({ title, description, icon, enabled, onToggle, children, badge }: Props) {
  return (
    <article className={`feature-card ${enabled ? 'on' : ''}`}>
      <header className="feature-head">
        <div className="feature-icon">{icon}</div>
        <div className="feature-titles">
          <div className="feature-title-row">
            <h3>{title}</h3>
            {badge && <span className="badge">{badge}</span>}
          </div>
          <p>{description}</p>
        </div>
        <label className="switch" title={enabled ? 'Enabled' : 'Disabled'}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
          />
          <span className="slider" />
        </label>
      </header>
      {enabled && children && <div className="feature-body">{children}</div>}
    </article>
  )
}
