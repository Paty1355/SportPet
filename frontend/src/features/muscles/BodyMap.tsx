import { StyleSheet, Text, View } from 'react-native'
import Svg, { Circle, Ellipse, G, Path, Rect } from 'react-native-svg'
import { useTheme } from '../../lib/theme'
import { REGION_LABELS, regionsFor, type RegionId } from './muscleRegions'

type Shape =
  | { kind: 'ellipse'; cx: number; cy: number; rx: number; ry: number }
  | { kind: 'circle'; cx: number; cy: number; r: number }
  | { kind: 'rect'; x: number; y: number; w: number; h: number; rx?: number }
  | { kind: 'path'; d: string }

interface Region {
  id: RegionId
  shape: Shape
}

// Figure drawn in a 200 x 410 box. Front and back views share the outline.
const FRONT: Region[] = [
  { id: 'shoulders', shape: { kind: 'circle', cx: 56, cy: 96, r: 16 } },
  { id: 'shoulders', shape: { kind: 'circle', cx: 144, cy: 96, r: 16 } },
  { id: 'chest', shape: { kind: 'path', d: 'M70 96 Q100 112 98 140 L74 136 Q66 116 70 96 Z' } },
  { id: 'chest', shape: { kind: 'path', d: 'M130 96 Q100 112 102 140 L126 136 Q134 116 130 96 Z' } },
  { id: 'biceps', shape: { kind: 'ellipse', cx: 50, cy: 140, rx: 9, ry: 26 } },
  { id: 'biceps', shape: { kind: 'ellipse', cx: 150, cy: 140, rx: 9, ry: 26 } },
  { id: 'forearms', shape: { kind: 'ellipse', cx: 44, cy: 202, rx: 8, ry: 28 } },
  { id: 'forearms', shape: { kind: 'ellipse', cx: 156, cy: 202, rx: 8, ry: 28 } },
  { id: 'obliques', shape: { kind: 'path', d: 'M72 140 L80 144 L80 200 L70 196 Z' } },
  { id: 'obliques', shape: { kind: 'path', d: 'M128 140 L120 144 L120 200 L130 196 Z' } },
  { id: 'abs', shape: { kind: 'rect', x: 80, y: 144, w: 40, h: 56, rx: 8 } },
  { id: 'quads', shape: { kind: 'ellipse', cx: 84, cy: 270, rx: 16, ry: 50 } },
  { id: 'quads', shape: { kind: 'ellipse', cx: 116, cy: 270, rx: 16, ry: 50 } },
  { id: 'adductors', shape: { kind: 'ellipse', cx: 97, cy: 290, rx: 5, ry: 28 } },
  { id: 'adductors', shape: { kind: 'ellipse', cx: 103, cy: 290, rx: 5, ry: 28 } },
]

const BACK: Region[] = [
  { id: 'traps', shape: { kind: 'path', d: 'M100 64 L130 80 L120 100 L100 116 L80 100 L70 80 Z' } },
  { id: 'rear-deltoids', shape: { kind: 'circle', cx: 56, cy: 96, r: 16 } },
  { id: 'rear-deltoids', shape: { kind: 'circle', cx: 144, cy: 96, r: 16 } },
  { id: 'lats', shape: { kind: 'path', d: 'M66 110 Q62 150 80 176 L92 150 L86 110 Z' } },
  { id: 'lats', shape: { kind: 'path', d: 'M134 110 Q138 150 120 176 L108 150 L114 110 Z' } },
  { id: 'triceps', shape: { kind: 'ellipse', cx: 50, cy: 140, rx: 9, ry: 26 } },
  { id: 'triceps', shape: { kind: 'ellipse', cx: 150, cy: 140, rx: 9, ry: 26 } },
  { id: 'forearms', shape: { kind: 'ellipse', cx: 44, cy: 202, rx: 8, ry: 28 } },
  { id: 'forearms', shape: { kind: 'ellipse', cx: 156, cy: 202, rx: 8, ry: 28 } },
  { id: 'lower-back', shape: { kind: 'rect', x: 88, y: 160, w: 24, h: 46, rx: 8 } },
  { id: 'glutes', shape: { kind: 'ellipse', cx: 84, cy: 230, rx: 18, ry: 16 } },
  { id: 'glutes', shape: { kind: 'ellipse', cx: 116, cy: 230, rx: 18, ry: 16 } },
  { id: 'hamstrings', shape: { kind: 'ellipse', cx: 84, cy: 290, rx: 16, ry: 48 } },
  { id: 'hamstrings', shape: { kind: 'ellipse', cx: 116, cy: 290, rx: 16, ry: 48 } },
  { id: 'calves', shape: { kind: 'ellipse', cx: 84, cy: 366, rx: 13, ry: 30 } },
  { id: 'calves', shape: { kind: 'ellipse', cx: 116, cy: 366, rx: 13, ry: 30 } },
]

// Silhouette shared by both views.
const OUTLINE = [
  { kind: 'circle' as const, cx: 100, cy: 40, r: 24 },
  { kind: 'rect' as const, x: 92, y: 62, w: 16, h: 14, rx: 0 },
  { kind: 'rect' as const, x: 38, y: 78, w: 124, h: 22, rx: 0 },
  { kind: 'path' as const, d: 'M62 80 L138 80 L146 100 L140 200 L128 215 L72 215 L60 200 L54 100 Z' },
  { kind: 'rect' as const, x: 40, y: 118, w: 20, h: 110, rx: 10 },
  { kind: 'rect' as const, x: 140, y: 118, w: 20, h: 110, rx: 10 },
  { kind: 'rect' as const, x: 68, y: 210, w: 30, h: 190, rx: 14 },
  { kind: 'rect' as const, x: 102, y: 210, w: 30, h: 190, rx: 14 },
]

export function BodyMap({ primary, secondary }: { primary: string[]; secondary: string[] }) {
  const { colors } = useTheme()
  const primaryIds = regionsFor(primary)
  const secondaryIds = regionsFor(secondary)
  const shown = [...primaryIds, ...secondaryIds].map((id) => REGION_LABELS[id])

  function fillFor(id: RegionId) {
    if (primaryIds.has(id)) return { fill: colors.primary, opacity: 0.95 }
    if (secondaryIds.has(id)) return { fill: colors.primary, opacity: 0.4 }
    return { fill: colors.border, opacity: 0.6 }
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <View style={styles.figure}>
          <Text style={[styles.view, { color: colors.muted }]}>Front</Text>
          <Figure regions={FRONT} fillFor={fillFor} />
        </View>
        <View style={styles.figure}>
          <Text style={[styles.view, { color: colors.muted }]}>Back</Text>
          <Figure regions={BACK} fillFor={fillFor} />
        </View>
      </View>

      <Text style={[styles.caption, { color: colors.muted }]}>
        {shown.length > 0
          ? `Highlighted: ${[...new Set(shown)].join(', ')}`
          : 'No muscles from the model could be shown on the map.'}
      </Text>
    </View>
  )
}

function Figure({
  regions,
  fillFor,
}: {
  regions: Region[]
  fillFor: (id: RegionId) => { fill: string; opacity: number }
}) {
  const { colors } = useTheme()
  return (
    <Svg width="100%" height={260} viewBox="0 0 200 410">
      <G>
        {OUTLINE.map((s, i) => (
          <OutlineShape key={i} shape={s} color={colors.surface} stroke={colors.border} />
        ))}
      </G>
      {regions.map((region, i) => {
        const style = fillFor(region.id)
        return (
          <ShapeNode key={`${region.id}-${i}`} shape={region.shape} fill={style.fill} opacity={style.opacity} />
        )
      })}
    </Svg>
  )
}

function OutlineShape({
  shape,
  color,
  stroke,
}: {
  shape: (typeof OUTLINE)[number]
  color: string
  stroke: string
}) {
  const common = { fill: color, stroke, strokeWidth: 1.5 }
  if (shape.kind === 'circle') return <Circle cx={shape.cx} cy={shape.cy} r={shape.r} {...common} />
  if (shape.kind === 'rect') {
    return <Rect x={shape.x} y={shape.y} width={shape.w} height={shape.h} rx={shape.rx} {...common} />
  }
  return <Path d={shape.d} {...common} />
}

function ShapeNode({ shape, fill, opacity }: { shape: Shape; fill: string; opacity: number }) {
  const common = { fill, opacity }
  if (shape.kind === 'ellipse') {
    return <Ellipse cx={shape.cx} cy={shape.cy} rx={shape.rx} ry={shape.ry} {...common} />
  }
  if (shape.kind === 'circle') return <Circle cx={shape.cx} cy={shape.cy} r={shape.r} {...common} />
  if (shape.kind === 'rect') {
    return <Rect x={shape.x} y={shape.y} width={shape.w} height={shape.h} rx={shape.rx} {...common} />
  }
  return <Path d={shape.d} {...common} />
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  row: { flexDirection: 'row', justifyContent: 'space-around', gap: 12 },
  figure: { flex: 1, alignItems: 'center', maxWidth: 200 },
  view: { fontSize: 12, fontWeight: '600', marginBottom: 4 },
  caption: { fontSize: 13, textAlign: 'center' },
})
