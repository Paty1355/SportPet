import type { ReactNode } from 'react'
import { Gesture, GestureDetector } from 'react-native-gesture-handler'
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated'

interface DraggableFoodProps {
  children: ReactNode
  onDragStart: () => void
  onMove: (x: number, y: number) => void
  onDrop: (x: number, y: number) => void
}

export function DraggableFood({ children, onDragStart, onMove, onDrop }: DraggableFoodProps) {
  const offsetX = useSharedValue(0)
  const offsetY = useSharedValue(0)

  const pan = Gesture.Pan()
    .onStart(() => {
      runOnJS(onDragStart)()
    })
    .onUpdate((event) => {
      offsetX.value = event.translationX
      offsetY.value = event.translationY
      runOnJS(onMove)(event.absoluteX, event.absoluteY)
    })
    .onEnd((event) => {
      runOnJS(onDrop)(event.absoluteX, event.absoluteY)
      offsetX.value = withSpring(0)
      offsetY.value = withSpring(0)
    })

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: offsetX.value }, { translateY: offsetY.value }],
  }))

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={animatedStyle}>{children}</Animated.View>
    </GestureDetector>
  )
}
