// Body-map regions. The ids are the contract with the backend (app/schemas/vision.py): the card's muscle lists
// come back as these exact ids. Each id is drawn in BodyMap.tsx.
export type RegionId =
  | 'chest'
  | 'shoulders'
  | 'rear-deltoids'
  | 'biceps'
  | 'triceps'
  | 'forearms'
  | 'abs'
  | 'obliques'
  | 'traps'
  | 'lats'
  | 'lower-back'
  | 'glutes'
  | 'quads'
  | 'hamstrings'
  | 'calves'
  | 'adductors'

export const REGION_LABELS: Record<RegionId, string> = {
  chest: 'Chest',
  shoulders: 'Front shoulders',
  'rear-deltoids': 'Rear shoulders',
  biceps: 'Biceps',
  triceps: 'Triceps',
  forearms: 'Forearms',
  abs: 'Abs',
  obliques: 'Obliques',
  traps: 'Traps',
  lats: 'Lats',
  'lower-back': 'Lower back',
  glutes: 'Glutes',
  quads: 'Quads',
  hamstrings: 'Hamstrings',
  calves: 'Calves',
  adductors: 'Inner thigh',
}

export function isRegionId(value: string): value is RegionId {
  return Object.prototype.hasOwnProperty.call(REGION_LABELS, value)
}

export function labelOf(id: string): string {
  return isRegionId(id) ? REGION_LABELS[id] : id
}

// Keeps only known region ids; anything else from the backend is ignored.
export function regionsFor(ids: string[]): Set<RegionId> {
  return new Set(ids.filter(isRegionId))
}
