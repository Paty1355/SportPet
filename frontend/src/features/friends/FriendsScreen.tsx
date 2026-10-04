import { useState } from 'react'
import { Screen } from '../../components/Screen'
import { useAuth } from '../../lib/auth'
import { FriendsSection } from './FriendsSection'

export function FriendsScreen() {
  const { token, user } = useAuth()
  const [sharePet, setSharePet] = useState(user?.share_pet ?? true)

  return <Screen>{token && <FriendsSection token={token} sharePet={sharePet} onSharePetChange={setSharePet} />}</Screen>
}
