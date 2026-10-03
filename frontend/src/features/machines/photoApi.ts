import { Platform } from 'react-native'
import { API_URL, ApiError } from '../../lib/api'

export interface PhotoAgentReply {
  reply: string
  memories_used: string[]
}

export interface PickedPhoto {
  uri: string
  mimeType?: string | null
  fileName?: string | null
}

const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']

function resolveMimeType(photo: PickedPhoto): string {
  if (photo.mimeType && ALLOWED.includes(photo.mimeType)) return photo.mimeType
  const name = (photo.fileName ?? photo.uri).toLowerCase()
  if (name.endsWith('.png')) return 'image/png'
  if (name.endsWith('.webp')) return 'image/webp'
  return 'image/jpeg'
}

export async function analyzePhoto(token: string, photo: PickedPhoto, message: string): Promise<PhotoAgentReply> {
  const type = resolveMimeType(photo)
  const name = photo.fileName ?? `machine.${type.split('/')[1] === 'jpeg' ? 'jpg' : type.split('/')[1]}`

  const form = new FormData()
  if (Platform.OS === 'web') {
    const blob = await (await fetch(photo.uri)).blob()
    form.append('file', new File([blob], name, { type }))
  } else {
    form.append('file', { uri: photo.uri, name, type } as unknown as Blob)
  }
  form.append('message', message)

  const response = await fetch(`${API_URL}/agents/photo`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`
    throw new ApiError(response.status, detail)
  }
  return response.json()
}
