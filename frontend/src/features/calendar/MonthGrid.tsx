import { Pressable, StyleSheet, Text, View } from 'react-native'
import { WEEKDAY_LABELS, toISODate } from '../../lib/dates'
import type { TrainingCalendar } from '../../lib/types'
import { useTheme } from '../../lib/theme'

interface MonthGridProps {
  cells: (Date | null)[]
  calendar: TrainingCalendar
  selectedISO: string
  onSelect: (iso: string) => void
}

export function MonthGrid({ cells, calendar, selectedISO, onSelect }: MonthGridProps) {
  const { colors } = useTheme()
  const todayISO = toISODate(new Date())

  return (
    <View>
      <View style={styles.row}>
        {WEEKDAY_LABELS.map((label) => (
          <Text key={label} style={[styles.weekday, { color: colors.muted }]}>
            {label}
          </Text>
        ))}
      </View>

      <View style={styles.grid}>
        {cells.map((date, index) => {
          if (!date) return <View key={`empty-${index}`} style={styles.cell} />

          const iso = toISODate(date)
          const workoutCount = calendar[iso]?.workouts.length ?? 0
          const selected = iso === selectedISO
          const isToday = iso === todayISO

          return (
            <View key={iso} style={styles.cell}>
              <Pressable
                onPress={() => onSelect(iso)}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                style={[
                  styles.day,
                  selected && { backgroundColor: colors.primary },
                  isToday && !selected && { borderWidth: 1, borderColor: colors.primary },
                ]}
              >
                <Text style={[styles.dayText, { color: selected ? '#ffffff' : colors.text }, selected && styles.bold]}>
                  {date.getDate()}
                </Text>
                {workoutCount > 0 && (
                  <View style={[styles.dot, { backgroundColor: selected ? '#ffffff' : colors.primary }]} />
                )}
              </Pressable>
            </View>
          )
        })}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', paddingBottom: 8 },
  weekday: { flex: 1, textAlign: 'center', fontSize: 12, fontWeight: '600' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '14.2857%', aspectRatio: 1, padding: 3 },
  day: { flex: 1, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  dayText: { fontSize: 14 },
  bold: { fontWeight: '700' },
  dot: { width: 6, height: 6, borderRadius: 3, marginTop: 3 },
})
