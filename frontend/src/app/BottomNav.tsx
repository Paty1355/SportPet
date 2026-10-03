import { NavLink } from 'react-router-dom'
import { navItems } from './navItems'

export function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg md:hidden dark:border-slate-800 dark:bg-slate-950/90">
      <ul className="mx-auto grid max-w-md grid-cols-5 items-end px-2">
        {navItems.map(({ to, label, icon: Icon, primary }) => (
          <li key={to} className="flex justify-center">
            <NavLink
              to={to}
              end={to === '/'}
              aria-label={label}
              className={({ isActive }) =>
                primary
                  ? `-mt-6 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/40 transition active:scale-95 ${isActive ? 'ring-4 ring-indigo-200 dark:ring-indigo-900' : ''}`
                  : `flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition ${
                      isActive
                        ? 'text-indigo-600 dark:text-indigo-400'
                        : 'text-slate-500 dark:text-slate-400'
                    }`
              }
            >
              <Icon size={primary ? 26 : 22} />
              {!primary && <span>{label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
