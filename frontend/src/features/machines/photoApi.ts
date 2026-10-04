import { File as LocalFile } from 'expo-file-system'
import { Platform } from 'react-native'
import { API_URL, ApiError } from '../../lib/api'

export interface VisionResponse {
  machine_id: string
  machine_name: string
  category: string
  sources: string[]
  description: string
  primary_muscles: string[]
  secondary_muscles: string[]
  setup_steps: string[]
  exercise_steps: string[]
  tips: string[]
}

export interface PickedPhoto {
  uri: string
  mimeType?: string | null
  fileName?: string | null
}

// Formats the backend decodes (it checks the file content, not this label).
const MIME_BY_EXTENSION: Record<string, string> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
  heic: 'image/heic',
  heif: 'image/heif',
  avif: 'image/avif',
  bmp: 'image/bmp',
  tif: 'image/tiff',
  tiff: 'image/tiff',
  gif: 'image/gif',
}

function resolveMimeType(photo: PickedPhoto): string {
  if (photo.mimeType?.startsWith('image/')) return photo.mimeType
  const extension = (photo.fileName ?? photo.uri).split('?')[0].split('.').pop()?.toLowerCase() ?? ''
  return MIME_BY_EXTENSION[extension] ?? 'image/jpeg'
}

// FastAPI returns a string for our own errors and a list of {msg} for validation errors (e.g. missing file).
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item as { msg?: unknown })?.msg)
      .filter((msg): msg is string => typeof msg === 'string')
    if (messages.length) return messages.join('; ')
  }
  return `Request failed (${status})`
}

export async function analyzeMachine(photo: PickedPhoto): Promise<VisionResponse> {
  const type = resolveMimeType(photo)
  const name = photo.fileName ?? `machine.${type.split('/')[1]}`

  const form = new FormData()
  if (Platform.OS === 'web') {
    const blob = await (await fetch(photo.uri)).blob()
    form.append('file', new File([blob], name, { type }))
  } else {
    // Expo's fetch rejects React Native's { uri } file parts ("Unsupported FormDataPart implementation");
    // it accepts a File from expo-file-system instead.
    form.append('file', new LocalFile(photo.uri) as unknown as Blob, name)
  }

  const response = await fetch(`${API_URL}/agents/vision/analyze`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    if (response.status === 413) {
      throw new ApiError(413, 'This photo is too large. Use one up to 10 MB and 60 megapixels.')
    }
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, errorMessage(body, response.status))
  }
  return response.json()
}
