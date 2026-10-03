import AsyncStorage from '@react-native-async-storage/async-storage'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, fetchMe, login, register, type UserOut } from './api'

const TOKEN_KEY = 'auth-token'

interface AuthContextValue {
  user: UserOut | null
  token: string | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, name: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    AsyncStorage.getItem(TOKEN_KEY)
      .then(async (stored) => {
        if (!stored) return
        const me = await fetchMe(stored)
        if (!cancelled) {
          setUser(me)
          setToken(stored)
        }
      })
      .catch(async (error) => {
        if (error instanceof ApiError && error.status === 401) {
          await AsyncStorage.removeItem(TOKEN_KEY).catch(() => {})
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      signIn: async (email, password) => {
        const accessToken = await login(email, password)
        const me = await fetchMe(accessToken)
        await AsyncStorage.setItem(TOKEN_KEY, accessToken)
        setToken(accessToken)
        setUser(me)
      },
      signUp: async (email, password, name) => {
        await register(email, password, name)
        const accessToken = await login(email, password)
        const me = await fetchMe(accessToken)
        await AsyncStorage.setItem(TOKEN_KEY, accessToken)
        setToken(accessToken)
        setUser(me)
      },
      signOut: () => {
        AsyncStorage.removeItem(TOKEN_KEY).catch(() => {})
        setToken(null)
        setUser(null)
      },
    }),
    [user, token, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
