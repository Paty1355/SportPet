import { StyleSheet, useWindowDimensions, View } from 'react-native'
import Svg, { Circle, Defs, Pattern, Rect } from 'react-native-svg'
import { useTheme } from '../lib/theme'

const SPACING = 24

export function DotPattern() {
  const { colors } = useTheme()
  const { width, height } = useWindowDimensions()

  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.layer]}>
      <Svg width={width} height={height}>
        <Defs>
          <Pattern id="app-dots" width={SPACING} height={SPACING} patternUnits="userSpaceOnUse">
            <Circle cx={SPACING / 2} cy={SPACING / 2} r={1.2} fill={colors.neutralSoft} opacity={0.6} />
          </Pattern>
        </Defs>
        <Rect width={width} height={height} fill="url(#app-dots)" />
      </Svg>
    </View>
  )
}

const styles = StyleSheet.create({
  layer: { zIndex: -1 },
})
