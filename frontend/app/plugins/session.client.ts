// Runs once on client startup and hydrates session state from the cookie-backed API.
// Do not block app bootstrap indefinitely if the backend is unavailable.
export default defineNuxtPlugin(() => {
  const session = useSessionState()
  if (!session.value.authenticated) {
    apiFetch("/auth/session/")
      .then((payload) => {
        session.value = {
          ...payload,
          hydrated: true,
        }
      })
      .catch(() => {
        // no valid session or backend unavailable
      })
      .finally(() => {
        if (!session.value.hydrated) {
          session.value = {
            ...session.value,
            hydrated: true,
          }
        }
      })
  } else if (!session.value.hydrated) {
    session.value = {
      ...session.value,
      hydrated: true,
    }
  }
})
