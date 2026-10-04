import { useCallback, useEffect, useState } from 'react'
import { Pressable, StyleSheet, Switch, Text, TextInput, View } from 'react-native'
import { ApiError } from '../../lib/api'
import { useTheme } from '../../lib/theme'
import { findCosmetic } from '../pet/cosmetics'
import { MiniPet } from '../pet/MiniPet'
import {
  acceptRequest,
  fetchFriendPet,
  fetchFriends,
  fetchRequests,
  rejectRequest,
  removeFriend,
  searchUsers,
  sendRequest,
  updateSharePet,
  type Friend,
  type FriendPet,
  type FriendRequests,
  type UserSearchResult,
} from './friendsApi'

export function FriendsSection({
  token,
  sharePet,
  onSharePetChange,
}: {
  token: string
  sharePet: boolean
  onSharePetChange: (value: boolean) => void
}) {
  const { colors } = useTheme()
  const [friends, setFriends] = useState<Friend[]>([])
  const [pets, setPets] = useState<Record<number, FriendPet | null>>({})
  const [requests, setRequests] = useState<FriendRequests>({ incoming: [], outgoing: [] })
  const [openFriendId, setOpenFriendId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<UserSearchResult[] | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const reload = useCallback(async () => {
    const [list, pending] = await Promise.all([fetchFriends(token), fetchRequests(token)])
    setFriends(list)
    setRequests(pending)
    const loaded = await Promise.all(list.map((friend) => fetchFriendPet(token, friend.id).catch(() => null)))
    setPets(Object.fromEntries(list.map((friend, index) => [friend.id, loaded[index]])))
  }, [token])

  useEffect(() => {
    reload().catch(() => {})
  }, [reload])

  function showError(caught: unknown) {
    setMessage(caught instanceof ApiError || caught instanceof Error ? caught.message : 'Something went wrong')
  }

  async function search() {
    const email = query.trim()
    if (email.length < 3) {
      setMessage('Type the full e-mail address of your friend.')
      return
    }
    setMessage(null)
    try {
      setResults(await searchUsers(token, email))
    } catch (caught) {
      showError(caught)
    }
  }

  async function invite(userId: number) {
    try {
      await sendRequest(token, userId)
      setResults(null)
      setQuery('')
      setMessage('Invitation sent. Waiting for acceptance.')
      await reload()
    } catch (caught) {
      showError(caught)
    }
  }

  async function respond(friendshipId: number, accept: boolean) {
    try {
      if (accept) await acceptRequest(token, friendshipId)
      else await rejectRequest(token, friendshipId)
      await reload()
    } catch (caught) {
      showError(caught)
    }
  }

  async function unfriend(friendId: number) {
    try {
      await removeFriend(token, friendId)
      setOpenFriendId(null)
      await reload()
    } catch (caught) {
      showError(caught)
    }
  }

  async function toggleShare(value: boolean) {
    onSharePetChange(value)
    try {
      await updateSharePet(token, value)
    } catch (caught) {
      onSharePetChange(!value)
      showError(caught)
    }
  }

  const card = { backgroundColor: colors.surface, borderColor: colors.border }

  return (
    <View style={[styles.card, card]}>
      <Text style={[styles.title, { color: colors.text }]}>Friends</Text>

      <View style={styles.row}>
        <Text style={[styles.label, { color: colors.text }]}>Share my pet with friends</Text>
        <Switch value={sharePet} onValueChange={toggleShare} trackColor={{ true: colors.primary }} />
      </View>

      <View style={styles.searchRow}>
        <TextInput
          value={query}
          onChangeText={(text) => {
            setQuery(text)
            setResults(null)
          }}
          placeholder="Friend's e-mail"
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          keyboardType="email-address"
          style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]}
        />
        <Pressable onPress={search} accessibilityRole="button" style={[styles.button, { backgroundColor: colors.primary }]}>
          <Text style={styles.buttonText}>Search</Text>
        </Pressable>
      </View>

      {results && results.length === 0 && <Text style={[styles.meta, { color: colors.muted }]}>No one found with that e-mail.</Text>}
      {results?.map((user) => (
        <View key={user.id} style={styles.row}>
          <Text style={[styles.label, { color: colors.text }]}>{user.name ?? 'User'}</Text>
          <Pressable onPress={() => invite(user.id)} accessibilityRole="button" style={[styles.smallButton, { backgroundColor: colors.primary }]}>
            <Text style={styles.buttonText}>Invite</Text>
          </Pressable>
        </View>
      ))}

      {requests.incoming.length > 0 && <Text style={[styles.section, { color: colors.primary }]}>Invitations</Text>}
      {requests.incoming.map((request) => (
        <View key={request.id} style={styles.row}>
          <Text style={[styles.label, { color: colors.text }]}>User #{request.requester_id}</Text>
          <View style={styles.actions}>
            <Pressable onPress={() => respond(request.id, true)} accessibilityRole="button" style={[styles.smallButton, { backgroundColor: colors.primary }]}>
              <Text style={styles.buttonText}>Accept</Text>
            </Pressable>
            <Pressable onPress={() => respond(request.id, false)} accessibilityRole="button" style={[styles.smallButton, { borderColor: colors.border, borderWidth: 1 }]}>
              <Text style={[styles.buttonText, { color: colors.muted }]}>Decline</Text>
            </Pressable>
          </View>
        </View>
      ))}

      {requests.outgoing.length > 0 && <Text style={[styles.section, { color: colors.primary }]}>Waiting for acceptance</Text>}
      {requests.outgoing.map((request) => (
        <Text key={request.id} style={[styles.meta, { color: colors.muted }]}>Invitation sent to user #{request.addressee_id}</Text>
      ))}

      <Text style={[styles.section, { color: colors.primary }]}>Your friends</Text>
      {friends.length === 0 && <Text style={[styles.meta, { color: colors.muted }]}>No friends yet.</Text>}
      {friends.map((friend) => {
        const pet = pets[friend.id]
        const open = openFriendId === friend.id
        return (
          <View key={friend.id} style={[styles.friend, { borderColor: colors.border }]}>
            <Pressable
              onPress={() => setOpenFriendId(open ? null : friend.id)}
              accessibilityRole="button"
              style={styles.row}
            >
              {pet ? (
                <MiniPet size={56} species={pet.species} body={pet.body} hat={pet.hat} />
              ) : (
                <View style={[styles.placeholder, { backgroundColor: colors.primarySoft }]} />
              )}
              <View style={styles.friendInfo}>
                <Text style={[styles.label, { color: colors.text }]}>{friend.name ?? 'Friend'}</Text>
                <Text style={[styles.meta, { color: colors.muted }]}>
                  {pet ? `${pet.name} · Level ${pet.level}` : 'Pet hidden'}
                </Text>
              </View>
              <Text style={[styles.meta, { color: colors.primary }]}>{open ? 'Hide' : 'Open'}</Text>
            </Pressable>

            {open && pet && <FriendPetDetail pet={pet} />}
            {open && (
              <Pressable onPress={() => unfriend(friend.id)} accessibilityRole="button">
                <Text style={[styles.meta, { color: colors.warn }]}>Remove friend</Text>
              </Pressable>
            )}
          </View>
        )
      })}

      {message && <Text style={[styles.meta, { color: colors.warn }]}>{message}</Text>}
    </View>
  )
}

function FriendPetDetail({ pet }: { pet: FriendPet }) {
  const { colors } = useTheme()
  const outfit = [pet.hat, pet.body, pet.background, pet.theme, ...(pet.decor ?? [])]
    .map((id) => findCosmetic(id)?.name)
    .filter((name): name is string => Boolean(name))

  return (
    <View style={[styles.detail, { backgroundColor: colors.bg, borderColor: colors.border }]}>
      <MiniPet size={160} species={pet.species} body={pet.body} hat={pet.hat} />
      <Text style={[styles.label, { color: colors.text }]}>
        {pet.name} · Level {pet.level}
      </Text>
      <Text style={[styles.meta, { color: colors.muted, textAlign: 'center' }]}>
        {outfit.length ? outfit.join(', ') : 'No outfit yet'}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 10 },
  title: { fontSize: 16, fontWeight: '700' },
  section: { fontSize: 13, fontWeight: '700', marginTop: 6 },
  label: { fontSize: 15, fontWeight: '600' },
  meta: { fontSize: 13 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  searchRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  input: { flex: 1, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 9, fontSize: 15 },
  button: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12 },
  smallButton: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 10 },
  buttonText: { color: '#ffffff', fontSize: 14, fontWeight: '700' },
  actions: { flexDirection: 'row', gap: 8 },
  friend: { gap: 8, paddingVertical: 6, borderBottomWidth: StyleSheet.hairlineWidth },
  friendInfo: { flex: 1, gap: 2 },
  placeholder: { width: 56, height: 56, borderRadius: 28 },
  detail: { borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, padding: 14, alignItems: 'center', gap: 8 },
})
