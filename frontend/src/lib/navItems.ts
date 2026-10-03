import type { ComponentProps } from 'react'
import type { Ionicons } from '@expo/vector-icons'

export type IconName = ComponentProps<typeof Ionicons>['name']

export interface NavItem {
  href: '/' | '/training' | '/machines' | '/diet' | '/pet' | '/profile'
  label: string
  icon: IconName
  accent: string
  primary?: boolean
}

export const navItems: NavItem[] = [
  { href: '/training', label: 'Training', icon: 'barbell-outline', accent: '#6366f1' },
  { href: '/machines', label: 'Machines', icon: 'camera-outline', accent: '#0ea5e9' },
  { href: '/', label: 'Calendar', icon: 'calendar-outline', accent: '#8b5cf6', primary: true },
  { href: '/diet', label: 'Diet', icon: 'nutrition-outline', accent: '#22c55e' },
  { href: '/pet', label: 'Pet', icon: 'paw-outline', accent: '#ec4899' },
  { href: '/profile', label: 'Profile', icon: 'person-outline', accent: '#64748b' },
]
