import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { Lightbox } from '../../components/Lightbox'
import { Screen } from '../../components/Screen'
import { ApiError } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { fetchDietPlan, generateDietPlan, mealImageSource, type DietMeal, type DietPlan } from './dietPlanApi'

export function DietPlanScreen() {
  const { colors } = useTheme()
  const { token } = useAuth()
  const [plan, setPlan] = useState<DietPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    fetchDietPlan(token)
      .then((saved) => {
        if (!cancelled) setPlan(saved)
      })
      .catch((caught) => {
        if (!cancelled) setError(messageOf(caught))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  async function generate() {
    if (!token) return
    setBusy(true)
    setError(null)
    try {
      setPlan(await generateDietPlan(token))
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setError('Finish the diet questionnaire in the chat first.')
      } else {
        setError(messageOf(caught))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>Your meal plan</Text>
        <Text style={[styles.meta, { color: colors.muted }]}>
          {plan ? `About ${plan.dailyCalories} kcal a day, built from your questionnaire and recent health data.` : 'A 7-day meal plan built from your questionnaire and recent health data.'}
        </Text>
        <Pressable
          onPress={generate}
          disabled={busy}
          accessibilityRole="button"
          style={[styles.button, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
        >
          {busy ? (
            <ActivityIndicator color={colors.muted} />
          ) : (
            <Text style={styles.buttonText}>{plan ? 'Generate a new plan' : 'Generate plan'}</Text>
          )}
        </Pressable>
        {busy && <Text style={[styles.meta, { color: colors.muted }]}>This can take up to a minute.</Text>}
        {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}
      </View>

      {loading && <ActivityIndicator color={colors.primary} />}

      {plan?.days.map((day) => (
        <View key={day.day} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[styles.meta, { color: colors.primary, fontWeight: '700' }]}>{day.day}</Text>
          {day.meals.map((meal) => (
            <MealRow key={`${day.day}-${meal.name}`} meal={meal} />
          ))}
        </View>
      ))}
    </Screen>
  )
}

function MealRow({ meal }: { meal: DietMeal }) {
  const { colors } = useTheme()
  return (
    <View style={[styles.meal, { borderColor: colors.border }]}>
      {meal.imageUrl ? (
        <Lightbox uri={mealImageSource(meal.imageUrl)} style={styles.photo} caption={meal.title} />
      ) : (
        <View style={[styles.photo, { backgroundColor: colors.primarySoft }]} />
      )}
      <View style={styles.mealText}>
        <Text style={[styles.meta, { color: colors.muted }]}>{meal.name}</Text>
        <Text style={[styles.mealTitle, { color: colors.text }]}>{meal.title}</Text>
        <Text style={[styles.meta, { color: colors.muted }]}>
          {meal.calories} kcal · P {meal.proteinGrams} g · C {meal.carbsGrams} g · F {meal.fatGrams} g · {meal.prepTimeMinutes} min
        </Text>
        <Text style={[styles.meta, { color: colors.text }]}>{meal.description}</Text>
      </View>
    </View>
  )
}

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : 'Something went wrong'
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 10 },
  title: { fontSize: 16, fontWeight: '700' },
  meta: { fontSize: 13 },
  button: { paddingVertical: 12, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  meal: { flexDirection: 'row', gap: 12, paddingTop: 10, borderTopWidth: StyleSheet.hairlineWidth },
  photo: { width: 88, height: 88, borderRadius: 12 },
  mealText: { flex: 1, gap: 4 },
  mealTitle: { fontSize: 15, fontWeight: '600' },
})
