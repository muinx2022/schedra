export type SessionPayload = {
  authenticated: boolean
  hydrated: boolean
  user?: {
    id: number
    email: string
    first_name: string
    last_name: string
    workspace?: {
      id: string
      name: string
      slug: string
      timezone: string
    }
  }
}

export const useSessionState = () =>
  useState<SessionPayload>("session", () => ({
    authenticated: false,
    hydrated: false,
  }))
