export interface Anchor {
  cx: number
  top: number
  scale: number
}

export interface SpeciesDef {
  id: string
  name: string
  anchor: Anchor
  defaultBody: string
}

// Nakrycia są rysowane w układzie królika (czubek głowy w 110, 74). Dla innego gatunku
// ten punkt przesuwamy na jego czubek głowy i skalujemy, dzięki czemu nakrycia pasują.
export const REFERENCE_ANCHOR: Anchor = { cx: 110, top: 74, scale: 1 }

export const SPECIES: SpeciesDef[] = [
  { id: 'bunny', name: 'Bunny', anchor: REFERENCE_ANCHOR, defaultBody: 'body-peach' },
  { id: 'snake', name: 'Snake', anchor: { cx: 110, top: 50, scale: 1 }, defaultBody: 'body-green' },
  { id: 'bear', name: 'Bear', anchor: { cx: 110, top: 62, scale: 1 }, defaultBody: 'body-cocoa' },
]

export function findSpecies(id: string | null | undefined): SpeciesDef {
  return SPECIES.find((species) => species.id === id) ?? SPECIES[0]
}

export function hatTransform(anchor: Anchor): string {
  const { cx, top, scale } = anchor
  return `translate(${cx} ${top}) scale(${scale}) translate(${-REFERENCE_ANCHOR.cx} ${-REFERENCE_ANCHOR.top})`
}
