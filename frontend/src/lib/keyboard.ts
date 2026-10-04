import { useEffect, useState } from 'react'
import { Keyboard, Platform } from 'react-native'

// Height of the on-screen keyboard on Android, 0 when hidden.
// Android runs edge-to-edge, so the system does not shrink the window when the keyboard opens.
// The app root uses this value as bottom padding, which moves the nav bar and inputs above the keyboard.
export function useKeyboardHeight(): number {
  const [height, setHeight] = useState(0)

  useEffect(() => {
    if (Platform.OS !== 'android') return
    const show = Keyboard.addListener('keyboardDidShow', (event) => setHeight(event.endCoordinates.height))
    const hide = Keyboard.addListener('keyboardDidHide', () => setHeight(0))
    return () => {
      show.remove()
      hide.remove()
    }
  }, [])

  return height
}
