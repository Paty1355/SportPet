import { useCallback, useRef, useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View, type LayoutRectangle } from 'react-native'
import { Screen } from '../../components/Screen'
import { useTheme } from '../../lib/theme'
import { DraggableCarrot } from './DraggableCarrot'
import { MOUTH_Y, PET_SIZE, PetCharacter } from './PetCharacter'
import { usePet } from './PetProvider'
import { levelOf, moodOf, XP_PER_LEVEL, type PetMood } from './petLogic'

const carrotImage = require('../../../assets/pet/carrot.png')
const PET_COOLDOWN_MS = 2000

const MOOD_TEXT: Record<PetMood, string> = {
  hungry: 'Hungry, feed me!',
  sad: 'Feeling a bit lonely',
  content: 'Doing okay',
  happy: 'Happy and full',
}

export function PetScreen() {
  const { colors } = useTheme()
  const { pet, feed, affection } = usePet()

  const avatarRef = useRef<View>(null)
  const avatarRect = useRef<LayoutRectangle | null>(null)
  const [pettingCount, setPettingCount] = useState(0)
  const [carrotNearby, setCarrotNearby] = useState(false)
  const lastPetAt = useRef(0)

  const handlePet = () => {
    const now = Date.now()
    if (now - lastPetAt.current < PET_COOLDOWN_MS) return
    lastPetAt.current = now
    affection()
    setPettingCount((count) => count + 1)
  }

  const measureAvatar = useCallback(() => {
    avatarRef.current?.measureInWindow((x, y, width, height) => {
      avatarRect.current = { x, y, width, height }
    })
  }, [])

  const handleCarrotMove = useCallback((x: number, y: number) => {
    const rect = avatarRect.current
    if (!rect) return
    const mouthX = rect.x + (rect.width - PET_SIZE) / 2 + PET_SIZE / 2
    const mouthY = rect.y + (rect.height - PET_SIZE) / 2 + MOUTH_Y
    const distance = Math.hypot(x - mouthX, y - mouthY)
    setCarrotNearby(distance < 60)
  }, [])

  const handleDrop = useCallback(
    (x: number, y: number) => {
      setCarrotNearby(false)
      const rect = avatarRect.current
      if (!rect) return
      const inside =
        x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height
      if (inside) feed()
    },
    [feed],
  )

  if (!pet) {
    return (
      <Screen>
        <Text style={{ color: colors.muted }}>Loading...</Text>
      </Screen>
    )
  }

  const mood = moodOf(pet)
  const level = levelOf(pet.xp)
  const xpInLevel = pet.xp % XP_PER_LEVEL
  const canFeed = pet.carrots > 0 && pet.fullness < 100

  const feedLabel =
    pet.fullness >= 100
      ? 'Bun is full'
      : pet.carrots === 0
        ? 'No carrots left'
        : 'Feed a carrot'

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View
          ref={avatarRef}
          onLayout={measureAvatar}
          style={[styles.stage, { backgroundColor: colors.primarySoft }]}
        >
          <View style={styles.ground} />
          <PetCharacter
            mood={mood}
            fullness={pet.fullness}
            pettingCount={pettingCount}
            carrotNearby={carrotNearby}
            onPet={handlePet}
          />
        </View>

        <Text style={[styles.name, { color: colors.text }]}>
          {pet.name} · Level {level}
        </Text>
        <Text style={[styles.mood, { color: colors.muted }]}>{MOOD_TEXT[mood]}</Text>

        <Bar label="XP to next level" valueText={`${xpInLevel}/${XP_PER_LEVEL}`} ratio={xpInLevel / XP_PER_LEVEL} color={colors.primary} />
        <Bar label="Fullness" valueText={`${Math.round(pet.fullness)}%`} ratio={pet.fullness / 100} color={colors.success} />
        <Bar label="Happiness" valueText={`${Math.round(pet.happiness)}%`} ratio={pet.happiness / 100} color={colors.warn} />

        <View style={[styles.basket, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <View style={styles.basketCount}>
            <Image source={carrotImage} style={styles.carrotIcon} />
            <Text style={[styles.carrotText, { color: colors.text }]}>x {pet.carrots}</Text>
          </View>

          <View style={styles.basketCenter}>
            {canFeed ? (
              <>
                <DraggableCarrot onDragStart={measureAvatar} onMove={handleCarrotMove} onDrop={handleDrop} />
                <Text style={[styles.dragHint, { color: colors.muted }]}>Drag onto Bun</Text>
              </>
            ) : (
              <Text style={[styles.dragHint, { color: colors.muted }]}>{feedLabel}</Text>
            )}
          </View>

          <Pressable
            onPress={feed}
            disabled={!canFeed}
            accessibilityRole="button"
            style={[styles.feedButton, { backgroundColor: canFeed ? colors.primary : colors.neutralSoft }]}
          >
            <Text style={[styles.feedText, { color: canFeed ? '#ffffff' : colors.muted }]}>Feed</Text>
          </Pressable>
        </View>

        <Text style={[styles.hint, { color: colors.muted }]}>
          Stroke Bun to pet it. Mark a workout as done in the calendar to earn carrots and XP.
        </Text>
      </View>
    </Screen>
  )
}

function Bar({
  label,
  valueText,
  ratio,
  color,
}: {
  label: string
  valueText: string
  ratio: number
  color: string
}) {
  const { colors } = useTheme()
  const width = `${Math.min(100, Math.max(0, ratio * 100))}%` as const

  return (
    <View style={styles.bar}>
      <View style={styles.barLabels}>
        <Text style={[styles.barLabel, { color: colors.muted }]}>{label}</Text>
        <Text style={[styles.barLabel, { color: colors.text }]}>{valueText}</Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.neutralSoft }]}>
        <View style={[styles.fill, { width, backgroundColor: color }]} />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 20, gap: 14 },
  stage: {
    height: 260,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  ground: {
    position: 'absolute',
    bottom: 26,
    width: 150,
    height: 18,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.12)',
  },
  name: { fontSize: 20, fontWeight: '700', textAlign: 'center' },
  mood: { fontSize: 14, textAlign: 'center', marginTop: -6 },
  bar: { gap: 6 },
  barLabels: { flexDirection: 'row', justifyContent: 'space-between' },
  barLabel: { fontSize: 13, fontWeight: '600' },
  track: { height: 10, borderRadius: 999, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 999 },
  basket: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
  },
  basketCount: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  carrotIcon: { width: 28, height: 28 },
  carrotText: { fontSize: 15, fontWeight: '600' },
  basketCenter: { flex: 1, alignItems: 'center', gap: 2 },
  dragHint: { fontSize: 12, textAlign: 'center' },
  feedButton: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 12 },
  feedText: { fontSize: 15, fontWeight: '700' },
  hint: { fontSize: 13, textAlign: 'center' },
})
