import { NavLink } from 'react-router-dom'
import { Dumbbell } from 'lucide-react'
import type { Theme } from '../lib/useTheme'
import { navItems } from './navItems'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  theme: Theme
  onToggleTheme: () => void
}

export function Sidebar({ theme, onToggleTheme }: SidebarProps) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-200 bg-white/80 p-4 backdrop-blur-lg md:flex dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/30">
          <Dumbbell size={20} />
        </div>
        <span className="text-lg font-bold tracking-tight">FitApp</span>
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30'
                  : 'text-slate-600 hover:bg-slate-200/70 dark:text-slate-300 dark:hover:bg-slate-800'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-slate-200 pt-4 dark:border-slate-800">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} showLabel />
      </div>
    </aside>
  )
}
