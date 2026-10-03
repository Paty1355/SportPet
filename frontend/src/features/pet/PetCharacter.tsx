import { Ionicons } from '@expo/vector-icons'
import { useEffect, useRef, useState } from 'react'
import { StyleSheet, View } from 'react-native'
import { Gesture, GestureDetector } from 'react-native-gesture-handler'
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated'
import Svg, { Circle, Ellipse, Path } from 'react-native-svg'
import type { PetMood } from './petLogic'

export const PET_SIZE = 220
export const MOUTH_Y = 152
const MOUTH_X = 110
const STROKE_STEP = 40
const BODY = '#fcd9a8'
const BODY_SHADE = '#f7c184'
const BELLY = '#fff3e0'
const BLUSH = '#f9a8d4'
const INK = '#3b2f2f'
const STAR = '#fbbf24'
const NOTE = '#818cf8'

const PETTING_ICONS = [
  { name: 'heart', color: BLUSH },
  { name: 'star', color: STAR },
  { name: 'musical-notes', color: NOTE },
] as const

interface PetCharacterProps {
  mood: PetMood
  fullness: number
  pettingCount: number
  carrotNearby: boolean
  onPet: () => void
}

export function PetCharacter({ mood, fullness, pettingCount, carrotNearby, onPet }: PetCharacterProps) {
  const bob = useSharedValue(0)
  const squash = useSharedValue(1)
  const blink = useSharedValue(1)
  const happyEyes = useSharedValue(1)
  const wiggle = useSharedValue(0)
  const nearOpen = useSharedValue(0)
  const chew = useSharedValue(0)
  const lastX = useSharedValue(0)
  const lastY = useSharedValue(0)
  const previousFullness = useRef(fullness)
  const previousPetting = useRef(pettingCount)
  const [feedCount, setFeedCount] = useState(0)

  useEffect(() => {
    bob.value = withRepeat(
      withSequence(withTiming(-8, { duration: 900 }), withTiming(0, { duration: 900 })),
      -1,
      false,
    )
  }, [bob])

  useEffect(() => {
    blink.value = withRepeat(
      withSequence(withDelay(2400, withTiming(0.1, { duration: 90 })), withTiming(1, { duration: 120 })),
      -1,
      false,
    )
  }, [blink])

  useEffect(() => {
    nearOpen.value = withTiming(carrotNearby ? 1 : 0, { duration: 150 })
  }, [carrotNearby, nearOpen])

  useEffect(() => {
    if (fullness > previousFullness.current) {
      squash.value = withSequence(withTiming(0.8, { duration: 120 }), withSpring(1, { damping: 6 }))
      chew.value = withSequence(
        withRepeat(withSequence(withTiming(1, { duration: 140 }), withTiming(0.2, { duration: 140 })), 4, false),
        withTiming(0, { duration: 120 }),
      )
      happyEyes.value = withSequence(withTiming(0.15, { duration: 80 }), withDelay(900, withTiming(1, { duration: 150 })))
      setFeedCount((count) => count + 1)
    }
    previousFullness.current = fullness
  }, [fullness, squash, chew, happyEyes])

  useEffect(() => {
    if (pettingCount === previousPetting.current) return
    previousPetting.current = pettingCount
    const direction = pettingCount % 2 === 0 ? 1 : -1
    wiggle.value = withSequence(
      withTiming(-6 * direction, { duration: 80 }),
      withTiming(6 * direction, { duration: 140 }),
      withTiming(0, { duration: 80 }),
    )
    squash.value = withSequence(withTiming(0.9, { duration: 80 }), withSpring(1, { damping: 8 }))
    happyEyes.value = withSequence(withTiming(0.15, { duration: 80 }), withDelay(450, withTiming(1, { duration: 120 })))
  }, [pettingCount, wiggle, squash, happyEyes])

  const stroke = Gesture.Pan()
    .minDistance(0)
    .onStart((event) => {
      lastX.value = event.x
      lastY.value = event.y
      runOnJS(onPet)()
    })
    .onUpdate((event) => {
      if (Math.abs(event.x - lastX.value) + Math.abs(event.y - lastY.value) > STROKE_STEP) {
        lastX.value = event.x
        lastY.value = event.y
        runOnJS(onPet)()
      }
    })

  const bodyStyle = useAnimatedStyle(() => ({
    transform: [
      { translateY: bob.value },
      { rotate: `${wiggle.value}deg` },
      { scaleX: 2 - squash.value },
      { scaleY: squash.value },
    ],
  }))

  const eyeStyle = useAnimatedStyle(() => ({
    transform: [{ scaleY: blink.value * happyEyes.value }],
  }))

  const openMouthStyle = useAnimatedStyle(() => {
    const amount = Math.max(nearOpen.value, chew.value)
    return {
      opacity: amount > 0.05 ? 1 : 0,
      transform: [{ scaleY: 0.2 + amount * 0.8 }, { scaleX: 0.8 + amount * 0.2 }],
    }
  })

  const closedMouthStyle = useAnimatedStyle(() => ({
    opacity: 1 - Math.max(nearOpen.value, chew.value),
  }))

  const petIcon = PETTING_ICONS[pettingCount % PETTING_ICONS.length]

  return (
    <GestureDetector gesture={stroke}>
      <View style={styles.container}>
        {[-44, 0, 44].map((offsetX, index) => (
          <FloatingIcon
            key={`pet-${offsetX}`}
            trigger={pettingCount}
            name={petIcon.name}
            color={petIcon.color}
            offsetX={offsetX}
            delay={index * 120}
          />
        ))}
        {[-44, 0, 44].map((offsetX, index) => (
          <FloatingIcon
            key={`feed-${offsetX}`}
            trigger={feedCount}
            name="sparkles"
            color={STAR}
            offsetX={offsetX}
            delay={index * 150}
          />
        ))}

        <Animated.View style={[StyleSheet.absoluteFill, bodyStyle]}>
          <Svg width={PET_SIZE} height={PET_SIZE} viewBox="0 0 220 220">
            <Ellipse cx="84" cy="200" rx="16" ry="9" fill={BODY_SHADE} />
            <Ellipse cx="136" cy="200" rx="16" ry="9" fill={BODY_SHADE} />
            <Ellipse cx="72" cy="52" rx="22" ry="48" fill={BODY} />
            <Ellipse cx="148" cy="52" rx="22" ry="48" fill={BODY} />
            <Ellipse cx="72" cy="56" rx="11" ry="32" fill={BLUSH} />
            <Ellipse cx="148" cy="56" rx="11" ry="32" fill={BLUSH} />
            <Ellipse cx="110" cy="140" rx="74" ry="66" fill={BODY} />
            <Ellipse cx="110" cy="168" rx="40" ry="30" fill={BELLY} />
            <Circle cx="74" cy="146" r="11" fill={BLUSH} opacity={0.7} />
            <Circle cx="146" cy="146" r="11" fill={BLUSH} opacity={0.7} />
            <Ellipse cx="110" cy="128" rx="6" ry="4.5" fill={BLUSH} />
          </Svg>

          <Animated.View style={[StyleSheet.absoluteFill, closedMouthStyle]} pointerEvents="none">
            <Svg width={PET_SIZE} height={PET_SIZE} viewBox="0 0 220 220">
              <Mouth mood={mood} />
            </Svg>
          </Animated.View>

          <Animated.View style={[styles.openMouth, openMouthStyle]} />

          <Animated.View style={[styles.eye, styles.leftEye, eyeStyle]}>
            <View style={styles.shine} />
          </Animated.View>
          <Animated.View style={[styles.eye, styles.rightEye, eyeStyle]}>
            <View style={styles.shine} />
          </Animated.View>
        </Animated.View>
      </View>
    </GestureDetector>
  )
}

function FloatingIcon({
  trigger,
  name,
  color,
  offsetX,
  delay,
}: {
  trigger: number
  name: (typeof PETTING_ICONS)[number]['name'] | 'sparkles'
  color: string
  offsetX: number
  delay: number
}) {
  const rise = useSharedValue(0)
  const opacity = useSharedValue(0)
  const previousTrigger = useRef(trigger)

  useEffect(() => {
    if (trigger === previousTrigger.current) return
    previousTrigger.current = trigger
    rise.value = 0
    rise.value = withDelay(delay, withTiming(-70, { duration: 800 }))
    opacity.value = withDelay(
      delay,
      withSequence(withTiming(1, { duration: 100 }), withDelay(450, withTiming(0, { duration: 300 }))),
    )
  }, [trigger, delay, rise, opacity])

  const style = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: rise.value }],
  }))

  return (
    <Animated.View style={[styles.floating, { left: PET_SIZE / 2 - 18 + offsetX }, style]}>
      <Ionicons name={name} size={36} color={color} />
    </Animated.View>
  )
}

function Mouth({ mood }: { mood: PetMood }) {
  if (mood === 'hungry') {
    return <Ellipse cx={MOUTH_X} cy={MOUTH_Y} rx="8" ry="9" fill={INK} />
  }
  if (mood === 'sad') {
    return (
      <Path d="M 96 158 Q 110 146 124 158" stroke={INK} strokeWidth={4} strokeLinecap="round" fill="none" />
    )
  }
  if (mood === 'happy') {
    return (
      <Path d="M 96 146 Q 110 162 124 146" stroke={INK} strokeWidth={4} strokeLinecap="round" fill="none" />
    )
  }
  return <Path d="M 100 150 Q 110 154 120 150" stroke={INK} strokeWidth={4} strokeLinecap="round" fill="none" />
}

const styles = StyleSheet.create({
  container: { width: PET_SIZE, height: PET_SIZE },
  floating: { position: 'absolute', top: 30, opacity: 0 },
  openMouth: {
    position: 'absolute',
    top: MOUTH_Y - 9,
    left: MOUTH_X - 9,
    width: 18,
    height: 20,
    borderRadius: 9,
    backgroundColor: INK,
    opacity: 0,
  },
  eye: {
    position: 'absolute',
    top: 106,
    width: 16,
    height: 22,
    borderRadius: 8,
    backgroundColor: INK,
  },
  leftEye: { left: 80 },
  rightEye: { left: 124 },
  shine: {
    position: 'absolute',
    top: 4,
    left: 3,
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: '#ffffff',
  },
})
