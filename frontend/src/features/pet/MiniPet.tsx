import { StyleSheet, View } from 'react-native'
import { findCosmetic } from './cosmetics'
import { PET_SIZE, PetCharacter } from './PetCharacter'

const DEFAULT_PALETTE = ['#fcd9a8', '#f7c184', '#fff3e0']

export function MiniPet({
  size,
  species,
  body,
  hat,
}: {
  size: number
  species?: string | null
  body?: string | null
  hat?: string | null
}) {
  const palette = findCosmetic(body)?.palette ?? DEFAULT_PALETTE
  const scale = size / PET_SIZE
  const offset = (size - PET_SIZE) / 2

  return (
    <View style={[styles.frame, { width: size, height: size }]} pointerEvents="none">
      <View style={[styles.inner, { left: offset, top: offset, transform: [{ scale }] }]}>
        <PetCharacter
          mood="happy"
          fullness={80}
          pettingCount={0}
          carrotNearby={false}
          palette={palette}
          hat={hat ?? null}
          species={species ?? undefined}
          onPet={() => {}}
        />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  frame: { overflow: 'hidden' },
  inner: { position: 'absolute', width: PET_SIZE, height: PET_SIZE },
})
