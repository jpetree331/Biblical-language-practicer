/* Thin typed fetch wrapper for the local service. Lives outside lib/ because
   it uses fetch (Divergence Rule 2 keeps lib/ framework-free). */

export type Deck = {
  id: string
  name: string
  topic: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  card_count?: number
}

export type Card = {
  id: string
  deck_id: string
  card_type: string
  payload: Record<string, unknown>
  source: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail))
    this.status = status
    this.detail = detail
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail: unknown = res.statusText
    try {
      detail = (await res.json()).detail
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body: unknown) => request<T>('POST', url, body),
  patch: <T>(url: string, body: unknown) => request<T>('PATCH', url, body),
  delete: (url: string) => request<void>('DELETE', url),
}
