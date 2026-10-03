import { StyleSheet, View } from 'react-native'
import Svg, { Ellipse, G, Path, Rect } from 'react-native-svg'

const LIGHT_COLORS = ['#fde047', '#f9a8d4', '#86efac', '#93c5fd']

function PumpkinArt() {
  return (
    <G>
      <Ellipse cx="30" cy="32" rx="22" ry="18" fill="#f97316" />
      <Ellipse cx="22" cy="32" rx="6" ry="14" fill="#ea580c" opacity={0.5} />
      <Ellipse cx="38" cy="32" rx="6" ry="14" fill="#ea580c" opacity={0.5} />
      <Rect x="27" y="8" width="6" height="9" rx="2" fill="#65a30d" />
      <Path d="M 33 12 Q 44 4 47 12 Q 38 17 33 12 Z" fill="#84cc16" />
    </G>
  )
}

function FairyLights() {
  return (
    <View style={styles.lights}>
      {LIGHT_COLORS.concat(LIGHT_COLORS, [LIGHT_COLORS[0]]).map((color, index) => (
        <View key={index} style={[styles.bulb, { backgroundColor: color }]} />
      ))}
    </View>
  )
}

export function DecorLayer({ ids }: { ids: string[] }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {ids.includes('decor-lights') && <FairyLights />}
      {ids.includes('decor-pumpkin') && (
        <>
          <View style={[styles.pumpkin, { left: 12, bottom: 18 }]}>
            <Svg width={64} height={60} viewBox="0 0 60 56">
              <PumpkinArt />
            </Svg>
          </View>
          <View style={[styles.pumpkin, { left: 62, bottom: 14 }]}>
            <Svg width={46} height={43} viewBox="0 0 60 56">
              <PumpkinArt />
            </Svg>
          </View>
          <View style={[styles.pumpkin, { right: 14, bottom: 16 }]}>
            <Svg width={40} height={37} viewBox="0 0 60 56">
              <PumpkinArt />
            </Svg>
          </View>
        </>
      )}
    </View>
  )
}

export function DecorPreview({ id }: { id: string }) {
  if (id === 'decor-lights') {
    return (
      <View style={styles.previewLights}>
        {LIGHT_COLORS.map((color) => (
          <View key={color} style={[styles.bulb, { backgroundColor: color }]} />
        ))}
      </View>
    )
  }
  return (
    <Svg width={48} height={44} viewBox="0 0 60 56">
      <PumpkinArt />
    </Svg>
  )
}

const styles = StyleSheet.create({
  lights: {
    position: 'absolute',
    top: 8,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 10,
  },
  previewLights: { flexDirection: 'row', flexWrap: 'wrap', width: 44, gap: 4, justifyContent: 'center' },
  bulb: { width: 8, height: 8, borderRadius: 4 },
  pumpkin: { position: 'absolute' },
})
