export default defineNuxtRouteMiddleware(() => {
  if (import.meta.server) return

  const session = useSessionState()
  if (!session.value.hydrated) return
  if (!session.value.authenticated) {
    return navigateTo("/login")
  }
})
