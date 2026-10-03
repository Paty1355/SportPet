import { Moon, Sun } from 'lucide-react'
import type { Theme } from '../lib/useTheme'

interface ThemeToggleProps {
  theme: Theme
  onToggle: () => void
  showLabel?: boolean
}

export function ThemeToggle({ theme, onToggle, showLabel = false }: ThemeToggleProps) {
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className="inline-flex items-center gap-2 rounded-xl p-2 text-slate-600 transition hover:bg-slate-200/70 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
      {showLabel && <span className="text-sm">{isDark ? 'Light theme' : 'Dark theme'}</span>}
    </button>
  )
}
