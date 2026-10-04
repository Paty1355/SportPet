import { Ionicons } from '@expo/vector-icons'
import { Link } from 'expo-router'
import { LinearGradient } from 'expo-linear-gradient'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View, type LayoutRectangle } from 'react-native'
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated'
import { CoinBadge } from '../../components/CoinBadge'
import { Screen } from '../../components/Screen'
import type { IconName } from '../../lib/navItems'
import { playMunchSound, playPetSound, preloadSounds, useSoundOn } from '../../lib/sound'
import { useTheme } from '../../lib/theme'
import { findCosmetic } from './cosmetics'
import { DecorLayer } from './Decor'
import { DraggableFood } from './DraggableFood'
import { FoodArt } from './FoodArt'
import { MOUTH_Y, PET_SIZE, PetCharacter } from './PetCharacter'
import { usePet } from './PetProvider'
import { levelOf, moodOf, ownedCount, XP_PER_LEVEL, type PetMood } from './petLogic'
import { FOOD_ITEMS, type FoodItem } from './shop'

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
  const lastPetAt = useRef(0)
  const [pettingCount, setPettingCount] = useState(0)
  const [carrotNearby, setCarrotNearby] = useState(false)
  const [soundOn, toggleSound] = useSoundOn()

  useEffect(() => {
    preloadSounds()
  }, [])

  const handlePet = () => {
    const now = Date.now()
    if (now - lastPetAt.current < PET_COOLDOWN_MS) return
    lastPetAt.current = now
    affection()
    playPetSound()
    setPettingCount((count) => count + 1)
  }

  const measureAvatar = useCallback(() => {
    avatarRef.current?.measureInWindow((x, y, width, height) => {
      avatarRect.current = { x, y, width, height }
    })
  }, [])

  const handleFoodMove = useCallback((x: number, y: number) => {
    const rect = avatarRect.current
    if (!rect) return
    const mouthX = rect.x + (rect.width - PET_SIZE) / 2 + PET_SIZE / 2
    const mouthY = rect.y + (rect.height - PET_SIZE) / 2 + MOUTH_Y
    setCarrotNearby(Math.hypot(x - mouthX, y - mouthY) < 60)
  }, [])

  if (!pet) {
    return (
      <Screen>
        <Text style={{ color: colors.muted }}>Loading...</Text>
      </Screen>
    )
  }

  const backgroundPalette = findCosmetic(pet.equipped.background)?.palette ?? ['#e0e7ff', '#fbcfe8']
  const bodyPalette = findCosmetic(pet.equipped.body)?.palette ?? ['#fcd9a8', '#f7c184', '#fff3e0']
  const ownedFoods = FOOD_ITEMS.filter((food) => ownedCount(pet, food.id) > 0)
  const isFull = pet.fullness >= 100
  const mood = moodOf(pet)
  const level = levelOf(pet.xp)
  const xpInLevel = pet.xp % XP_PER_LEVEL

  const handleFoodDrop = (food: FoodItem, x: number, y: number) => {
    setCarrotNearby(false)
    const rect = avatarRect.current
    if (!rect || isFull) return
    const inside = x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height
    if (inside) {
      feed(food)
      playMunchSound()
    }
  }

  return (
    <Screen>
      <View style={styles.topRow}>
        <CoinBadge coins={pet.coins} />
        <View style={styles.rightGroup}>
        <Pressable
          onPress={toggleSound}
          accessibilityRole="button"
          accessibilityLabel={soundOn ? 'Mute sounds' : 'Unmute sounds'}
          style={[styles.soundButton, { backgroundColor: colors.surface, borderColor: colors.border }]}
        >
          <Ionicons name={soundOn ? 'volume-high-outline' : 'volume-mute-outline'} size={18} color={colors.muted} />
        </Pressable>
        <Link href="/shop" asChild>
          <Pressable accessibilityRole="link" style={{ ...styles.shopButton, backgroundColor: colors.primary }}>
            <Ionicons name="bag-handle-outline" size={16} color="#ffffff" />
            <Text style={styles.shopText}>Shop</Text>
          </Pressable>
        </Link>
        </View>
      </View>

      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View
          ref={avatarRef}
          onLayout={measureAvatar}
          style={[styles.stage, { backgroundColor: backgroundPalette[0] }]}
        >
          <LinearGradient
            colors={[`${backgroundPalette[1]}73`, `${backgroundPalette[1]}00`]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={StyleSheet.absoluteFill}
            pointerEvents="none"
          />
          <View style={[styles.sunGlow, { backgroundColor: colors.primary }]} />
          <View style={[styles.floor, { backgroundColor: backgroundPalette[1] }]} />
          <DecorLayer ids={pet.equipped.decor} />
          <View style={styles.ground} />
          <PetCharacter
            mood={mood}
            fullness={pet.fullness}
            pettingCount={pettingCount}
            carrotNearby={carrotNearby}
            palette={bodyPalette}
            hat={pet.equipped.hat}
            species={pet.species}
            onPet={handlePet}
          />
        </View>

        <Text style={[styles.name, { color: colors.text }]}>
          {pet.name} · Level {level}
        </Text>
        <Text style={[styles.mood, { color: colors.muted }]}>{MOOD_TEXT[mood]}</Text>

        <Bar icon="star" label="XP to next level" valueText={`${xpInLevel}/${XP_PER_LEVEL}`} ratio={xpInLevel / XP_PER_LEVEL} color={colors.primary} />
        <Bar icon="nutrition" label="Fullness" valueText={`${Math.round(pet.fullness)}%`} ratio={pet.fullness / 100} color={colors.success} />
        <Bar icon="heart" label="Happiness" valueText={`${Math.round(pet.happiness)}%`} ratio={pet.happiness / 100} color={colors.warn} />

        <View style={[styles.basket, { backgroundColor: colors.bg, borderColor: colors.border }]}>
          {ownedFoods.length === 0 ? (
            <Text style={[styles.hint, { color: colors.muted }]}>No food yet. Visit the shop to buy some.</Text>
          ) : (
            <>
              <View style={styles.foodRow}>
                {ownedFoods.map((food) => (
                  <View key={food.id} style={styles.foodItem}>
                    <DraggableFood
                      onDragStart={measureAvatar}
                      onMove={handleFoodMove}
                      onDrop={(x, y) => handleFoodDrop(food, x, y)}
                    >
                      <FoodArt food={food} size={56} />
                    </DraggableFood>
                    <Text style={[styles.foodCount, { color: colors.text }]}>x {ownedCount(pet, food.id)}</Text>
                  </View>
                ))}
              </View>
              <Text style={[styles.hint, { color: colors.muted }]}>
                {isFull ? 'Bun is full' : 'Drag any food onto Bun'}
              </Text>
            </>
          )}
        </View>

        <Text style={[styles.hint, { color: colors.muted }]}>
          Stroke Bun to pet it. Finish workouts to earn coins and carrots.
        </Text>
      </View>
    </Screen>
  )
}

function Bar({
  icon,
  label,
  valueText,
  ratio,
  color,
}: {
  icon: IconName
  label: string
  valueText: string
  ratio: number
  color: string
}) {
  const { colors } = useTheme()
  const clamped = Math.min(1, Math.max(0, ratio))
  const progress = useSharedValue(clamped)

  useEffect(() => {
    progress.value = withTiming(clamped, { duration: 500 })
  }, [clamped, progress])

  const fillStyle = useAnimatedStyle(() => ({ width: `${progress.value * 100}%` }))

  return (
    <View style={styles.bar}>
      <View style={styles.barLabels}>
        <View style={styles.barTitle}>
          <View style={[styles.barIcon, { backgroundColor: `${color}22` }]}>
            <Ionicons name={icon} size={14} color={color} />
          </View>
          <Text style={[styles.barLabel, { color: colors.muted }]}>{label}</Text>
        </View>
        <Text style={[styles.barValue, { color: colors.text }]}>{valueText}</Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.neutralSoft, borderColor: colors.border }]}>
        <Animated.View style={[styles.fill, { backgroundColor: color }, fillStyle]}>
          <View style={styles.shine} />
        </Animated.View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  coinChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999 },
  coinText: { fontSize: 15, fontWeight: '700' },
  shopButton: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999 },
  shopText: { color: '#ffffff', fontSize: 14, fontWeight: '700' },
  rightGroup: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  soundButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 20, gap: 14, marginTop: 12 },
  stage: {
    height: 260,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  floor: {
    position: 'absolute',
    bottom: -70,
    left: -30,
    right: -30,
    height: 130,
    borderRadius: 200,
    opacity: 0.55,
  },
  sunGlow: {
    position: 'absolute',
    top: -60,
    right: -50,
    width: 200,
    height: 200,
    borderRadius: 100,
    opacity: 0.6,
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
  bar: { gap: 8 },
  barLabels: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  barTitle: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  barIcon: { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  barLabel: { fontSize: 13, fontWeight: '600' },
  barValue: { fontSize: 13, fontWeight: '700' },
  track: { height: 14, borderRadius: 999, overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth },
  fill: { height: '100%', borderRadius: 999, justifyContent: 'flex-start' },
  shine: {
    height: '45%',
    marginHorizontal: 4,
    marginTop: 2,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },
  basket: { borderRadius: 18, borderWidth: StyleSheet.hairlineWidth, padding: 14, gap: 10 },
  foodRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-around', gap: 12 },
  foodItem: { alignItems: 'center', gap: 4, minWidth: 64 },
  foodCount: { fontSize: 12, fontWeight: '700' },
  hint: { fontSize: 13, textAlign: 'center' },
})
