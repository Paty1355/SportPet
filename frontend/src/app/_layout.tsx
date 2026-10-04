import { Ionicons } from '@expo/vector-icons'
import { Link, Slot, usePathname } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { ActivityIndicator, Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { LinearGradient } from 'expo-linear-gradient'
import { DotPattern } from '../components/DotPattern'
import { NavItemContent } from '../components/NavItemContent'
import { ThemeToggle } from '../components/ThemeToggle'
import { AuthScreen } from '../features/auth/AuthScreen'
import { PetProvider } from '../features/pet/PetProvider'
import { useKeyboardHeight } from '../lib/keyboard'
import { WIDE_BREAKPOINT } from '../lib/layout'
import { AuthProvider, useAuth } from '../lib/auth'
import { navItems } from '../lib/navItems'
import { ThemeProvider, useTheme } from '../lib/theme'
import { TrainingProvider } from '../lib/training'

export default function RootLayout() {
  const keyboardHeight = useKeyboardHeight()
  return (
    <GestureHandlerRootView style={styles.root}>
      <View style={[styles.root, { paddingBottom: keyboardHeight }]}>
        <ThemeProvider>
          <AuthProvider>
            <Gate />
          </AuthProvider>
        </ThemeProvider>
      </View>
    </GestureHandlerRootView>
  )
}

function Gate() {
  const { user, loading } = useAuth()
  const { colors } = useTheme()

  if (loading) {
    return (
      <View style={[styles.root, styles.center, { backgroundColor: colors.bg }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    )
  }

  if (!user) return <AuthScreen />

  return (
    <TrainingProvider>
      <PetProvider>
        <AppShell />
      </PetProvider>
    </TrainingProvider>
  )
}

function AppShell() {
  const { colors, theme } = useTheme()
  const { width } = useWindowDimensions()
  const insets = useSafeAreaInsets()
  const pathname = usePathname()
  const wide = width >= WIDE_BREAKPOINT

  const links = navItems.map((item) => (
    <Link key={item.href} href={item.href} asChild>
      <Pressable style={styles.link} accessibilityRole="link">
        <NavItemContent item={item} active={pathname === item.href} wide={wide} />
      </Pressable>
    </Link>
  ))

  return (
    <>
      <StatusBar style={theme === 'dark' ? 'light' : 'dark'} />
      <View style={[styles.root, wide && styles.rootWide, { backgroundColor: colors.bg }]}>
        <LinearGradient
          colors={[`${colors.primary}1F`, `${colors.primary}00`]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[StyleSheet.absoluteFill, styles.background]}
          pointerEvents="none"
        />
        <DotPattern />
        {wide ? (
          <View
            style={[
              styles.sidebar,
              { backgroundColor: colors.surface, borderColor: colors.border, paddingTop: insets.top + 24 },
            ]}
          >
            <Brand />
            <View style={styles.sidebarList}>{links}</View>
            <View style={styles.flexFill} />
            <View style={[styles.sidebarFooter, { borderColor: colors.border }]}>
              <ThemeToggle showLabel />
            </View>
          </View>
        ) : (
          <View style={[styles.header, { paddingTop: insets.top + 8, borderColor: colors.border }]}>
            <Brand />
            <ThemeToggle />
          </View>
        )}

        <View style={styles.content}>
          <Slot />
        </View>

        {!wide && (
          <View
            style={[
              styles.bottomBar,
              { backgroundColor: colors.surface, borderColor: colors.border, paddingBottom: insets.bottom },
            ]}
          >
            {links}
          </View>
        )}
      </View>
    </>
  )
}

function Brand() {
  const { colors } = useTheme()
  return (
    <View style={styles.brand}>
      <View style={[styles.brandMark, { backgroundColor: colors.primary }]}>
        <Ionicons name="barbell" size={18} color="#ffffff" />
      </View>
      <Text style={[styles.brandText, { color: colors.text }]}>SportPet</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  center: { alignItems: 'center', justifyContent: 'center' },
  background: { zIndex: -2 },
  rootWide: { flexDirection: 'row' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  content: { flex: 1 },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  sidebar: {
    width: 240,
    paddingHorizontal: 16,
    paddingBottom: 24,
    borderRightWidth: StyleSheet.hairlineWidth,
  },
  sidebarList: { marginTop: 32, gap: 4 },
  sidebarFooter: { borderTopWidth: StyleSheet.hairlineWidth, paddingTop: 16 },
  flexFill: { flex: 1 },
  link: { flex: 1, alignItems: 'center' },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  brandMark: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  brandText: { fontSize: 18, fontWeight: '700' },
})
