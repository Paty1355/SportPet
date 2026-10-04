import { authGet, authRequest } from '../../lib/api'

export interface Friend {
  id: number
  name: string | null
}

export interface Friendship {
  id: number
  requester_id: number
  addressee_id: number
  status: string
}

export interface FriendRequests {
  incoming: Friendship[]
  outgoing: Friendship[]
}

export interface FriendPet {
  name: string
  species?: string | null
  level: number
  hat: string | null
  body: string | null
  background: string | null
  decor: string[] | null
  theme: string | null
}

export interface UserSearchResult {
  id: number
  name: string | null
}

export function fetchFriends(token: string) {
  return authGet<Friend[]>('/friends/', token)
}

export function fetchRequests(token: string) {
  return authGet<FriendRequests>('/friends/requests', token)
}

export function searchUsers(token: string, email: string) {
  return authGet<UserSearchResult[]>('/users/search', token, { email })
}

export function sendRequest(token: string, userId: number) {
  return authRequest<Friendship>('POST', '/friends/requests', token, { user_id: userId })
}

export function acceptRequest(token: string, friendshipId: number) {
  return authRequest<{ status: string }>('POST', `/friends/requests/${friendshipId}/accept`, token)
}

export function rejectRequest(token: string, friendshipId: number) {
  return authRequest<{ status: string }>('POST', `/friends/requests/${friendshipId}/reject`, token)
}

export function removeFriend(token: string, friendId: number) {
  return authRequest<{ status: string }>('DELETE', `/friends/${friendId}`, token)
}

export function fetchFriendPet(token: string, friendId: number) {
  return authGet<FriendPet>(`/friends/${friendId}/pet`, token)
}

export function updateSharePet(token: string, sharePet: boolean) {
  return authRequest<{ share_pet: boolean }>('PATCH', '/me/privacy', token, { share_pet: sharePet })
}

export function putMyPet(token: string, pet: FriendPet) {
  return authRequest<FriendPet>('PUT', '/me/pet', token, pet)
}
