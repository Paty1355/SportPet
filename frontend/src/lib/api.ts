export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

export interface UserOut {
  id: number
  email: string
  name: string | null
  created_at: string
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => null)
  let message = `Request failed (${response.status})`
  if (typeof body?.detail === 'string') {
    message = body.detail
  } else if (Array.isArray(body?.detail)) {
    message = body.detail.map((item: { msg: string }) => item.msg).join(', ')
  }
  return new ApiError(response.status, message)
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }).toString(),
  })
  if (!response.ok) throw await toApiError(response)
  const body: { access_token: string } = await response.json()
  return body.access_token
}

export async function register(email: string, password: string, name: string): Promise<UserOut> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name: name.trim() || null }),
  })
  if (!response.ok) throw await toApiError(response)
  return response.json()
}

export async function fetchMe(token: string): Promise<UserOut> {
  const response = await fetch(`${API_URL}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw await toApiError(response)
  return response.json()
}
