import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { useTheme } from '../../lib/theme'
import { useAuth } from '../../lib/auth'

type Mode = 'login' | 'register'

export function AuthScreen() {
  const { colors } = useTheme()
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const isRegister = mode === 'register'

  async function submit() {
    setError(null)
    setBusy(true)
    try {
      if (isRegister) {
        await signUp(email.trim(), password, name)
      } else {
        await signIn(email.trim(), password)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const inputStyle = [styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>{isRegister ? 'Create account' : 'Welcome back'}</Text>
        <Text style={[styles.subtitle, { color: colors.muted }]}>
          {isRegister ? 'Sign up to save your training and pet.' : 'Log in to continue your training.'}
        </Text>

        {isRegister && (
          <>
            <Text style={[styles.label, { color: colors.muted }]}>Name</Text>
            <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={colors.muted} style={inputStyle} />
          </>
        )}

        <Text style={[styles.label, { color: colors.muted }]}>Email</Text>
        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          style={inputStyle}
        />

        <Text style={[styles.label, { color: colors.muted }]}>Password</Text>
        <TextInput
          value={password}
          onChangeText={setPassword}
          placeholder="At least 8 characters"
          placeholderTextColor={colors.muted}
          secureTextEntry
          style={inputStyle}
        />

        {error && <Text style={[styles.error, { color: colors.warn }]}>{error}</Text>}

        <Pressable
          onPress={submit}
          disabled={busy || !email || !password}
          accessibilityRole="button"
          style={[
            styles.submit,
            { backgroundColor: busy || !email || !password ? colors.neutralSoft : colors.primary },
          ]}
        >
          <Text style={[styles.submitText, { color: busy || !email || !password ? colors.muted : '#ffffff' }]}>
            {busy ? 'Please wait...' : isRegister ? 'Sign up' : 'Log in'}
          </Text>
        </Pressable>

        <Pressable
          onPress={() => {
            setError(null)
            setMode(isRegister ? 'login' : 'register')
          }}
          accessibilityRole="button"
        >
          <Text style={[styles.switch, { color: colors.primary }]}>
            {isRegister ? 'Already have an account? Log in' : 'No account yet? Sign up'}
          </Text>
        </Pressable>
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 20, gap: 8, marginTop: 24 },
  title: { fontSize: 22, fontWeight: '700' },
  subtitle: { fontSize: 14, marginBottom: 8 },
  label: { fontSize: 13, marginTop: 6 },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  error: { fontSize: 14, marginTop: 4 },
  submit: { paddingVertical: 14, borderRadius: 14, alignItems: 'center', marginTop: 8 },
  submitText: { fontSize: 16, fontWeight: '700' },
  switch: { textAlign: 'center', fontSize: 14, fontWeight: '600', marginTop: 8 },
})
