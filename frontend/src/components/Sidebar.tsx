import type { LucideIcon } from 'lucide-react'
import {
  Clapperboard,
  FolderOpen,
  History,
  LayoutDashboard,
  Settings,
  Sparkles,
} from 'lucide-react'

type NavId = 'dashboard' | 'new' | 'projects' | 'history' | 'settings'

const NAV: { id: NavId; label: string; icon: LucideIcon }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'new', label: 'New Edit', icon: Sparkles },
  { id: 'projects', label: 'Projects', icon: FolderOpen },
  { id: 'history', label: 'History', icon: History },
  { id: 'settings', label: 'Settings', icon: Settings },
]

interface Props {
  active: NavId
  onNavigate: (id: NavId) => void
}

export function Sidebar({ active, onNavigate }: Props) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Clapperboard size={20} strokeWidth={2.2} />
        </div>
        <div>
          <div className="brand-name">AutoCut</div>
          <div className="brand-tag">AI Video Editor</div>
        </div>
      </div>

      <nav className="nav">
        {NAV.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${active === item.id ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <p>Upload → Select → Auto Edit</p>
      </div>
    </aside>
  )
}

export type { NavId }
