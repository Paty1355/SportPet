import type { ComponentProps } from 'react'
import type { Ionicons } from '@expo/vector-icons'

export type IconName = ComponentProps<typeof Ionicons>['name']

export interface NavItem {
  href: '/agents' | '/' | '/pet' | '/friends' | '/profile'
  label: string
  icon: IconName
  accent: string
  primary?: boolean
}

export const navItems: NavItem[] = [
  { href: '/agents', label: 'Agents', icon: 'sparkles-outline', accent: '#6366f1' },
  { href: '/', label: 'Calendar', icon: 'calendar-outline', accent: '#8b5cf6' },
  { href: '/pet', label: 'Pet', icon: 'paw-outline', accent: '#ec4899', primary: true },
  { href: '/friends', label: 'Friends', icon: 'people-outline', accent: '#0ea5e9' },
  { href: '/profile', label: 'Profile', icon: 'person-outline', accent: '#64748b' },
]
