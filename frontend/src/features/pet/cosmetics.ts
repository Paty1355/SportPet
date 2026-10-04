export type CosmeticKind = 'hat' | 'background' | 'body' | 'decor' | 'theme' | 'species'

export interface CosmeticItem {
  id: string
  name: string
  kind: CosmeticKind
  price: number
  palette?: string[]
}

export const COSMETICS: CosmeticItem[] = [
  { id: 'hat-bow', name: 'Bow', kind: 'hat', price: 15 },
  { id: 'hat-wreath', name: 'Flower wreath', kind: 'hat', price: 25 },
  { id: 'hat-witch', name: 'Witch hat', kind: 'hat', price: 30 },
  { id: 'hat-pirate', name: 'Eye patch', kind: 'hat', price: 25 },
  { id: 'bg-plain', name: 'Plain', kind: 'background', price: 0, palette: ['#f8fafc', '#e2e8f0'] },
  { id: 'bg-pastel', name: 'Pastel', kind: 'background', price: 20, palette: ['#e0e7ff', '#fbcfe8'] },
  { id: 'bg-autumn', name: 'Autumn', kind: 'background', price: 20, palette: ['#fde68a', '#fdba74'] },
  { id: 'bg-night', name: 'Night', kind: 'background', price: 35, palette: ['#312e81', '#1e1b4b'] },
  { id: 'body-peach', name: 'Peach', kind: 'body', price: 0, palette: ['#fcd9a8', '#f7c184', '#fff3e0'] },
  { id: 'body-mint', name: 'Mint', kind: 'body', price: 20, palette: ['#bbf7d0', '#86efac', '#ecfdf5'] },
  { id: 'body-lavender', name: 'Lavender', kind: 'body', price: 20, palette: ['#ddd6fe', '#c4b5fd', '#f5f3ff'] },
  { id: 'body-cocoa', name: 'Cocoa', kind: 'body', price: 30, palette: ['#d4a373', '#bc8a5f', '#f5e6d3'] },
  { id: 'body-green', name: 'Green', kind: 'body', price: 0, palette: ['#8fb996', '#5f7d64', '#f1ecc4'] },
  { id: 'decor-pumpkin', name: 'Pumpkin', kind: 'decor', price: 15 },
  { id: 'decor-lights', name: 'Fairy lights', kind: 'decor', price: 25 },
  { id: 'species-bunny', name: 'Bunny', kind: 'species', price: 0 },
  { id: 'species-bear', name: 'Bear', kind: 'species', price: 50 },
  { id: 'theme-indigo', name: 'Indigo', kind: 'theme', price: 0, palette: ['#4f46e5'] },
  { id: 'theme-rose', name: 'Rose', kind: 'theme', price: 20, palette: ['#db2777'] },
  { id: 'theme-mint', name: 'Mint', kind: 'theme', price: 20, palette: ['#059669'] },
  { id: 'theme-amber', name: 'Amber', kind: 'theme', price: 25, palette: ['#d97706'] },
  { id: 'theme-ocean', name: 'Ocean', kind: 'theme', price: 25, palette: ['#0284c7'] },
]

export const DEFAULT_OWNED = ['bg-plain', 'body-peach', 'body-green', 'theme-indigo', 'species-bunny']

export function findCosmetic(id: string | null | undefined): CosmeticItem | undefined {
  return COSMETICS.find((item) => item.id === id)
}
