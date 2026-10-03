import type { ComponentProps } from 'react'
import type { Ionicons } from '@expo/vector-icons'

export type IconName = ComponentProps<typeof Ionicons>['name']

export interface NavItem {
  href: '/' | '/training' | '/machines' | '/diet' | '/pet' | '/profile'
  label: string
  icon: IconName
  primary?: boolean
}

export const navItems: NavItem[] = [
  { href: '/training', label: 'Training', icon: 'barbell-outline' },
  { href: '/machines', label: 'Machines', icon: 'camera-outline' },
  { href: '/', label: 'Calendar', icon: 'calendar-outline', primary: true },
  { href: '/diet', label: 'Diet', icon: 'nutrition-outline' },
  { href: '/pet', label: 'Pet', icon: 'paw-outline' },
  { href: '/profile', label: 'Profile', icon: 'person-outline' },
]
