import { Outlet } from 'react-router-dom'
import { Dumbbell } from 'lucide-react'
import { useTheme } from '../lib/useTheme'
import { BottomNav } from './BottomNav'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'

export function AppShell() {
  const { theme, toggle } = useTheme()

  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      <div
        aria-hidden
        className="pointer-events-none fixed -top-40 right-[-10rem] h-[32rem] w-[32rem] rounded-full bg-indigo-400/20 blur-3xl dark:bg-indigo-600/10"
      />
      <div
        aria-hidden
        className="pointer-events-none fixed bottom-[-12rem] left-[-8rem] h-[28rem] w-[28rem] rounded-full bg-violet-400/20 blur-3xl dark:bg-violet-600/10"
      />

      <Sidebar theme={theme} onToggleTheme={toggle} />

      <div className="md:pl-64">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-4 py-3 backdrop-blur-lg md:hidden dark:border-slate-800 dark:bg-slate-950/80">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
              <Dumbbell size={16} />
            </div>
            <span className="font-bold tracking-tight">FitApp</span>
          </div>
          <ThemeToggle theme={theme} onToggle={toggle} />
        </header>

        <main className="relative mx-auto w-full max-w-5xl px-4 pb-28 pt-6 md:px-8 md:pb-12 md:pt-10">
          <Outlet />
        </main>
      </div>

      <BottomNav />
    </div>
  )
}
