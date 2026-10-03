import AsyncStorage from '@react-native-async-storage/async-storage'
import { useEffect, useState } from 'react'

const MUTE_KEY = 'sound-muted'

let muted = false

export function isSoundMuted(): boolean {
  return muted
}

export function useSoundOn(): [boolean, () => void] {
  const [soundOn, setSoundOn] = useState(!muted)

  useEffect(() => {
    AsyncStorage.getItem(MUTE_KEY)
      .then((value) => {
        muted = value === '1'
        setSoundOn(!muted)
      })
      .catch(() => {})
  }, [])

  const toggle = () => {
    muted = !muted
    setSoundOn(!muted)
    AsyncStorage.setItem(MUTE_KEY, muted ? '1' : '0').catch(() => {})
  }

  return [soundOn, toggle]
}
