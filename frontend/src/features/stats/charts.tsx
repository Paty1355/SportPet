import { useState } from 'react'
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native'
import Svg, { Line, Path, Rect } from 'react-native-svg'

const HEIGHT = 140

function useWidth(): [number, (event: LayoutChangeEvent) => void] {
  const [width, setWidth] = useState(0)
  return [width, (event) => setWidth(event.nativeEvent.layout.width)]
}

export function LineChart({
  values,
  band,
  color,
  gridColor,
  labels,
}: {
  values: (number | null)[]
  band?: { min: (number | null)[]; max: (number | null)[] }
  color: string
  gridColor: string
  labels?: string[]
}) {
  const [width, onLayout] = useWidth()
  const all = [...values, ...(band?.min ?? []), ...(band?.max ?? [])].filter((v): v is number => v !== null)
  if (width === 0 || all.length < 2) return <View onLayout={onLayout} style={{ height: HEIGHT }} />

  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const span = hi - lo || 1
  const step = width / Math.max(1, values.length - 1)
  const y = (v: number) => HEIGHT - 10 - ((v - lo) / span) * (HEIGHT - 20)

  const pathFor = (series: (number | null)[]) => {
    let d = ''
    series.forEach((v, i) => {
      if (v === null) return
      d += `${d === '' ? 'M' : 'L'} ${i * step} ${y(v)} `
    })
    return d
  }

  let bandPath = ''
  if (band) {
    const top: string[] = []
    const bottom: string[] = []
    band.max.forEach((v, i) => v !== null && top.push(`${i * step},${y(v)}`))
    band.min.forEach((v, i) => v !== null && bottom.unshift(`${i * step},${y(v)}`))
    bandPath = `M ${top.join(' L ')} L ${bottom.join(' L ')} Z`
  }

  return (
    <View onLayout={onLayout} style={{ height: HEIGHT }}>
      <Svg width={width} height={HEIGHT}>
        <Line x1={0} y1={HEIGHT - 10} x2={width} y2={HEIGHT - 10} stroke={gridColor} strokeWidth={1} />
        <Line x1={0} y1={10} x2={width} y2={10} stroke={gridColor} strokeWidth={1} strokeDasharray="4 4" />
        {band && bandPath !== '' && <Path d={bandPath} fill={color} opacity={0.18} />}
        <Path d={pathFor(values)} stroke={color} strokeWidth={2.5} fill="none" strokeLinejoin="round" />
      </Svg>
      {labels && labels.length > 0 && (
        <View style={styles.labelRow}>
          <Text style={[styles.label, { color: gridColor }]}>{labels[0]}</Text>
          <Text style={[styles.label, { color: gridColor }]}>{labels[labels.length - 1]}</Text>
        </View>
      )}
    </View>
  )
}

export function BarChart({
  values,
  color,
  gridColor,
  labels,
}: {
  values: (number | null)[]
  color: string
  gridColor: string
  labels: string[]
}) {
  const [width, onLayout] = useWidth()
  const max = Math.max(1, ...values.map((v) => v ?? 0))
  const slot = width / Math.max(1, values.length)
  const barWidth = Math.max(4, slot * 0.6)

  return (
    <View onLayout={onLayout} style={{ height: HEIGHT + 18 }}>
      {width > 0 && (
        <Svg width={width} height={HEIGHT}>
          <Line x1={0} y1={HEIGHT - 1} x2={width} y2={HEIGHT - 1} stroke={gridColor} strokeWidth={1} />
          {values.map((v, i) => {
            const h = v === null ? 0 : (v / max) * (HEIGHT - 12)
            return (
              <Rect
                key={i}
                x={i * slot + (slot - barWidth) / 2}
                y={HEIGHT - 1 - h}
                width={barWidth}
                height={h}
                rx={barWidth / 2}
                fill={color}
                opacity={v === null ? 0.15 : 1}
              />
            )
          })}
        </Svg>
      )}
      <View style={styles.labelRow}>
        <Text style={[styles.label, { color: gridColor }]}>{labels[0]}</Text>
        <Text style={[styles.label, { color: gridColor }]}>{labels[labels.length - 1]}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  labelRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  label: { fontSize: 11 },
})
