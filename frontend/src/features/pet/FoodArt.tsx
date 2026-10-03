import { Image, View } from 'react-native'
import Svg, { Ellipse, G, Path } from 'react-native-svg'
import type { FoodItem } from './shop'

export function FoodArt({ food, size }: { food: FoodItem; size: number }) {
  if (food.image) {
    return <Image source={food.image} style={{ width: size, height: size }} />
  }
  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size} viewBox="0 0 60 60">
        {food.art === 'hay' ? <HayArt /> : <GrassArt />}
      </Svg>
    </View>
  )
}

function HayArt() {
  return (
    <G>
      <Ellipse cx="30" cy="42" rx="26" ry="12" fill="#fde047" />
      <Path d="M 10 44 L 46 34" stroke="#eab308" strokeWidth={2} strokeLinecap="round" />
      <Path d="M 14 50 L 50 40" stroke="#ca8a04" strokeWidth={2} strokeLinecap="round" />
      <Path d="M 20 36 L 42 30" stroke="#eab308" strokeWidth={2} strokeLinecap="round" />
      <Path d="M 26 48 L 54 44" stroke="#ca8a04" strokeWidth={2} strokeLinecap="round" />
      <Path d="M 8 40 L 26 32" stroke="#ca8a04" strokeWidth={2} strokeLinecap="round" />
    </G>
  )
}

function GrassArt() {
  return (
    <G>
      <Path d="M 30 54 Q 24 32 14 20" stroke="#22c55e" strokeWidth={4} strokeLinecap="round" fill="none" />
      <Path d="M 30 54 Q 28 30 30 10" stroke="#16a34a" strokeWidth={4} strokeLinecap="round" fill="none" />
      <Path d="M 30 54 Q 36 32 46 22" stroke="#22c55e" strokeWidth={4} strokeLinecap="round" fill="none" />
      <Path d="M 30 54 Q 20 40 8 38" stroke="#4ade80" strokeWidth={3} strokeLinecap="round" fill="none" />
      <Path d="M 30 54 Q 40 40 52 38" stroke="#4ade80" strokeWidth={3} strokeLinecap="round" fill="none" />
    </G>
  )
}
