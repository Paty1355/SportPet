import { useEffect, useState, type ReactNode } from 'react'
import { Directory, File, Paths } from 'expo-file-system'
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { API_URL, ApiError } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { BarChart, LineChart } from '../stats/charts'
import {
  fetchDashboard,
  fetchHeartRateDay,
  type BloodPressure,
  type DailySummary,
  type Overview,
  type Series,
} from '../stats/statsApi'

interface StatsData {
  overview: Overview
  heartRate: Series
  daily: DailySummary[]
  bloodPressure: BloodPressure[]
}

export function ProfileScreen() {
  const { colors } = useTheme()
  const { user, token, signOut } = useAuth()
  const [stats, setStats] = useState<StatsData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    Promise.all([fetchDashboard(token), fetchHeartRateDay(token)])
      .then(([overview, heartRate]) => {
        if (!cancelled) {
          setStats({ overview, heartRate, daily: overview.daily, bloodPressure: overview.blood_pressure })
          setError(null)
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setStats(null)
          setError(caught instanceof Error ? caught.message : 'Unknown error')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.name, { color: colors.text }]}>{user?.name || 'Athlete'}</Text>
        <Text style={[styles.meta, { color: colors.muted }]}>
          {[
            stats?.overview.age ? `${stats.overview.age} y` : null,
            stats?.overview.bmi ? `BMI ${stats.overview.bmi}` : null,
            user?.email,
          ]
            .filter(Boolean)
            .join(' · ')}
        </Text>
        <Pressable onPress={signOut} accessibilityRole="button" style={[styles.signOut, { borderColor: colors.border }]}>
          <Text style={[styles.signOutText, { color: colors.warn }]}>Log out</Text>
        </Pressable>
      </View>

      {loading && <ActivityIndicator color={colors.primary} />}

      {!loading && !stats && (
        <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[styles.title, { color: colors.text }]}>No stats yet</Text>
          <Text style={[styles.meta, { color: colors.muted }]}>
            Stats appear once the demo history is loaded on the backend (generator/generate.py).
          </Text>
          {error && <Text style={[styles.meta, { color: colors.warn }]}>Error: {error}</Text>}
        </View>
      )}

      {stats && <StatsContent stats={stats} />}

      {stats && token && <ReportCard token={token} />}
    </Screen>
  )
}

function StatsContent({ stats }: { stats: StatsData }) {
  const { colors } = useTheme()
  const { overview, heartRate, daily, bloodPressure } = stats
  const lastDaily = daily.length > 0 ? daily[daily.length - 1] : null

  return (
    <>
      <View style={styles.tiles}>
        <Tile label="Heart rate" value={overview.latest.heart_rate ? `${Math.round(overview.latest.heart_rate.value)}` : '–'} unit="bpm" color={colors.warn} />
        <Tile label="SpO₂" value={overview.latest.spo2 ? `${Math.round(overview.latest.spo2.value)}` : '–'} unit="%" color={colors.success} />
        <Tile label="Stress" value={overview.latest.stress ? `${Math.round(overview.latest.stress.value)}` : '–'} unit="/100" color={colors.primary} />
        <Tile label="Steps" value={lastDaily?.steps != null ? `${lastDaily.steps}` : '–'} unit="today" color={colors.success} />
      </View>

      <ChartCard title="Heart rate · last 24 h" subtitle="Hourly average with min–max range">
        <LineChart
          values={heartRate.points.map((p) => p.value)}
          band={{ min: heartRate.points.map((p) => p.min), max: heartRate.points.map((p) => p.max) }}
          color={colors.warn}
          gridColor={colors.muted}
          labels={heartRate.points.length ? [formatTime(heartRate.points[0].ts), formatTime(heartRate.points[heartRate.points.length - 1].ts)] : []}
        />
      </ChartCard>

      <ChartCard title="Steps · last 14 days">
        <BarChart
          values={daily.map((d) => d.steps)}
          color={colors.success}
          gridColor={colors.muted}
          labels={daily.length ? [formatDay(daily[0].date), formatDay(daily[daily.length - 1].date)] : ['', '']}
        />
      </ChartCard>

      <ChartCard title="Sleep · last 14 days" subtitle="Hours per night">
        <BarChart
          values={daily.map((d) => (d.sleep_minutes != null ? Math.round((d.sleep_minutes / 60) * 10) / 10 : null))}
          color={colors.primary}
          gridColor={colors.muted}
          labels={daily.length ? [formatDay(daily[0].date), formatDay(daily[daily.length - 1].date)] : ['', '']}
        />
      </ChartCard>

      <ChartCard title="Blood pressure" subtitle="Systolic line, diastolic range">
        <LineChart
          values={bloodPressure.map((b) => b.systolic)}
          band={{ min: bloodPressure.map((b) => b.diastolic), max: bloodPressure.map((b) => b.systolic) }}
          color={colors.primary}
          gridColor={colors.muted}
          labels={bloodPressure.length ? [formatDay(bloodPressure[0].ts), formatDay(bloodPressure[bloodPressure.length - 1].ts)] : []}
        />
      </ChartCard>
    </>
  )
}

function ReportCard({ token }: { token: string }) {
  const { colors } = useTheme()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  async function download() {
    setBusy(true)
    setError(null)
    setSaved(null)
    try {
      const response = await fetch(`${API_URL}/health/report`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        throw new ApiError(response.status, `Request failed (${response.status})`)
      }
      if (Platform.OS === 'web') {
        const url = URL.createObjectURL(await response.blob())
        const link = document.createElement('a')
        link.href = url
        link.download = 'raport.pdf'
        link.click()
        URL.revokeObjectURL(url)
      } else {
        const bytes = new Uint8Array(await response.arrayBuffer())
        if (Platform.OS === 'android') {
          // The user picks the folder (e.g. Downloads); the file is written there without opening any other app.
          const folder = await Directory.pickDirectoryAsync()
          folder.createFile('raport.pdf', 'application/pdf').write(bytes)
          setSaved('Saved the report to the folder you picked.')
        } else {
          // iOS has no Downloads folder. The file goes to the app's Documents, visible in the Files app.
          const file = new File(Paths.document, 'raport.pdf')
          if (file.exists) file.delete()
          file.create()
          file.write(bytes)
          setSaved('Saved the report. Find it in Files, under SportPet.')
        }
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 422) {
        setError('Not enough data to generate a report yet. Keep logging workouts and measurements.')
      } else {
        setError(caught instanceof Error ? caught.message : 'Something went wrong')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.title, { color: colors.text }]}>Report for your doctor</Text>
      <Text style={[styles.meta, { color: colors.muted }]}>
        A PDF with your trends from the last 60 days. Needs enough data in the history.
      </Text>
      <Pressable
        onPress={download}
        disabled={busy}
        accessibilityRole="button"
        style={[styles.reportButton, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
      >
        {busy ? (
          <ActivityIndicator color={colors.muted} />
        ) : (
          <Text style={styles.reportButtonText}>Download report (PDF)</Text>
        )}
      </Pressable>
      {saved && <Text style={[styles.meta, { color: colors.success }]}>{saved}</Text>}
      {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}
    </View>
  )
}

function Tile({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  const { colors } = useTheme()
  return (
    <View style={[styles.tile, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={[styles.tileDot, { backgroundColor: color }]} />
      <Text style={[styles.tileLabel, { color: colors.muted }]}>{label}</Text>
      <Text style={[styles.tileValue, { color: colors.text }]}>
        {value} <Text style={[styles.tileUnit, { color: colors.muted }]}>{unit}</Text>
      </Text>
    </View>
  )
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  const { colors } = useTheme()
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
      {subtitle && <Text style={[styles.meta, { color: colors.muted }]}>{subtitle}</Text>}
      {children}
    </View>
  )
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatDay(iso: string): string {
  const d = new Date(iso)
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}`
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 10 },
  name: { fontSize: 20, fontWeight: '700' },
  title: { fontSize: 16, fontWeight: '700' },
  meta: { fontSize: 13 },
  signOut: { marginTop: 8, paddingVertical: 12, borderRadius: 12, borderWidth: 1, alignItems: 'center' },
  signOutText: { fontSize: 15, fontWeight: '700' },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: { flexGrow: 1, flexBasis: '45%', borderRadius: 18, borderWidth: StyleSheet.hairlineWidth, padding: 14, gap: 4 },
  tileDot: { width: 8, height: 8, borderRadius: 4 },
  tileLabel: { fontSize: 12, fontWeight: '600' },
  tileValue: { fontSize: 22, fontWeight: '700' },
  tileUnit: { fontSize: 12, fontWeight: '600' },
  reportButton: { paddingVertical: 14, borderRadius: 14, alignItems: 'center' },
  reportButtonText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
})
