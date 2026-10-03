import { Camera, CalendarDays, Dumbbell, Salad, User, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  primary?: boolean
}

export const navItems: NavItem[] = [
  { to: '/trening', label: 'Training', icon: Dumbbell },
  { to: '/maszyny', label: 'Machines', icon: Camera },
  { to: '/', label: 'Calendar', icon: CalendarDays, primary: true },
  { to: '/dieta', label: 'Diet', icon: Salad },
  { to: '/profil', label: 'Profile', icon: User },
]
