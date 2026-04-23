export default defineNuxtRouteMiddleware(async () => {
  if (import.meta.server) return

  const session = useSessionState()
  const localePath = useLocalePath()

  if (!session.value.hydrated) {
    try {
      const payload = await apiFetch<any>("/auth/session/")
      session.value = {
        ...payload,
        hydrated: true,
      }
    } catch {
      session.value = {
        authenticated: false,
        hydrated: true,
      }
    }
  }

  if (!session.value.authenticated) {
    return navigateTo(localePath("/login"))
  }
})
