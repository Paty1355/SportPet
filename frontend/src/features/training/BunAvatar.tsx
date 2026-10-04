import { StyleSheet, View } from 'react-native'
import { useTheme } from '../../lib/theme'
import { findCosmetic } from '../pet/cosmetics'
import { PET_SIZE, PetCharacter } from '../pet/PetCharacter'
import { usePet } from '../pet/PetProvider'

const AVATAR_SIZE = 52
const SCALE = 0.23

export function BunAvatar() {
  const { colors } = useTheme()
  const { pet } = usePet()
  const palette = findCosmetic(pet?.equipped.body ?? null)?.palette ?? ['#fcd9a8', '#f7c184', '#fff3e0']

  return (
    <View style={styles.frame} pointerEvents="none">
      <View style={[styles.circle, { backgroundColor: colors.primarySoft }]} />
      <View style={styles.inner}>
        <PetCharacter
          mood="happy"
          fullness={80}
          pettingCount={0}
          carrotNearby={false}
          palette={palette}
          hat={pet?.equipped.hat ?? null}
          species={pet?.species}
          onPet={() => {}}
        />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  frame: { width: AVATAR_SIZE, height: AVATAR_SIZE },
  circle: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: AVATAR_SIZE,
    height: AVATAR_SIZE,
    borderRadius: AVATAR_SIZE / 2,
  },
  inner: {
    position: 'absolute',
    width: PET_SIZE,
    height: PET_SIZE,
    left: (AVATAR_SIZE - PET_SIZE) / 2,
    top: (AVATAR_SIZE - PET_SIZE) / 2,
    transform: [{ scale: SCALE }],
  },
})
