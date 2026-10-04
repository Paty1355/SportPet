type Point = [number, number]

// Linia środkowa węża: od czubka szyi, przez falę, do końca ogona.
const CENTER: Point[] = [
  [110, 120],
  [110, 156],
  [104, 184],
  [132, 198],
  [166, 190],
  [190, 170],
  [206, 146],
  [210, 126],
]

const SAMPLES_PER_SEGMENT = 10
const NECK_WIDTH = 26
const TIP_WIDTH = 6

function catmullRom(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const t2 = t * t
  const t3 = t2 * t
  const component = (a: number, b: number, c: number, d: number) =>
    0.5 *
    (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
  return [component(p0[0], p1[0], p2[0], p3[0]), component(p0[1], p1[1], p2[1], p3[1])]
}

function smoothCenter(): Point[] {
  const points: Point[] = []
  for (let i = 0; i < CENTER.length - 1; i++) {
    const p0 = CENTER[Math.max(0, i - 1)]
    const p1 = CENTER[i]
    const p2 = CENTER[i + 1]
    const p3 = CENTER[Math.min(CENTER.length - 1, i + 2)]
    for (let s = 0; s < SAMPLES_PER_SEGMENT; s++) {
      points.push(catmullRom(p0, p1, p2, p3, s / SAMPLES_PER_SEGMENT))
    }
  }
  points.push(CENTER[CENTER.length - 1])
  return points
}

// Zamknięty kontur ciała: grubość maleje płynnie od szyi do końca ogona.
export function snakeBodyPath(): string {
  const center = smoothCenter()
  const last = center.length - 1
  const left: Point[] = []
  const right: Point[] = []

  center.forEach((point, index) => {
    const before = center[Math.max(0, index - 1)]
    const after = center[Math.min(last, index + 1)]
    const dx = after[0] - before[0]
    const dy = after[1] - before[1]
    const length = Math.hypot(dx, dy) || 1
    const nx = -dy / length
    const ny = dx / length
    const t = index / last
    const half = (NECK_WIDTH - (NECK_WIDTH - TIP_WIDTH) * Math.pow(t, 1.2)) / 2
    left.push([point[0] + nx * half, point[1] + ny * half])
    right.push([point[0] - nx * half, point[1] - ny * half])
  })

  const outline = [...left, ...right.reverse()]
  return `M ${outline.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ')} Z`
}
