import type { LucideIcon } from 'lucide-react'

interface ComingSoonPageProps {
  title: string
  description: string
  icon: LucideIcon
}

export function ComingSoonPage({ title, description, icon: Icon }: ComingSoonPageProps) {
  return (
    <div className="flex flex-col items-center rounded-3xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center backdrop-blur dark:border-slate-700 dark:bg-slate-900/60">
      <div className="mb-5 rounded-2xl bg-indigo-500/10 p-4 text-indigo-600 dark:text-indigo-300">
        <Icon size={32} />
      </div>
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">{description}</p>
      <span className="mt-6 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
        Coming soon
      </span>
    </div>
  )
}
