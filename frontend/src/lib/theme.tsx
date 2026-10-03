import AsyncStorage from '@react-native-async-storage/async-storage'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useColorScheme } from 'react-native'

export type Theme = 'light' | 'dark'

const lightPalette = {
  bg: '#f8fafc',
  surface: '#ffffff',
  border: '#e2e8f0',
  text: '#0f172a',
  muted: '#64748b',
  primary: '#4f46e5',
  primarySoft: '#e0e7ff',
  success: '#047857',
  successSoft: '#d1fae5',
  warn: '#b45309',
  warnSoft: '#fef3c7',
  neutral: '#475569',
  neutralSoft: '#e2e8f0',
}

export type Palette = typeof lightPalette

const darkPalette: Palette = {
  bg: '#020617',
  surface: '#0f172a',
  border: '#1e293b',
  text: '#f1f5f9',
  muted: '#94a3b8',
  primary: '#6366f1',
  primarySoft: '#312e81',
  success: '#6ee7b7',
  successSoft: '#064e3b',
  warn: '#fcd34d',
  warnSoft: '#78350f',
  neutral: '#cbd5e1',
  neutralSoft: '#334155',
}

export const palettes: Record<Theme, Palette> = { light: lightPalette, dark: darkPalette }

const STORAGE_KEY = 'theme'

interface ThemeContextValue {
  theme: Theme
  colors: Palette
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemTheme: Theme = useColorScheme() === 'dark' ? 'dark' : 'light'
  const [override, setOverride] = useState<Theme | null>(null)

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (value === 'light' || value === 'dark') setOverride(value)
      })
      .catch(() => {})
  }, [])

  const theme = override ?? systemTheme

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      colors: palettes[theme],
      toggle: () => {
        const next: Theme = theme === 'dark' ? 'light' : 'dark'
        setOverride(next)
        AsyncStorage.setItem(STORAGE_KEY, next).catch(() => {})
      },
    }),
    [theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used inside ThemeProvider')
  return context
}
