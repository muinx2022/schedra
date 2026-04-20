export type ThemePreference = "light" | "dark" | "system"

const STORAGE_KEY = "social-man-theme"
const OPTIONS: ThemePreference[] = ["system", "light", "dark"]

export function useThemePreference() {
  const preference = useState<ThemePreference>("theme-preference", () => "system")

  function applyTheme(value: ThemePreference) {
    if (!import.meta.client) return
    const root = document.documentElement
    root.dataset.themePreference = value
    if (value === "system") {
      delete root.dataset.theme
    } else {
      root.dataset.theme = value
    }
  }

  function setPreference(value: ThemePreference) {
    preference.value = OPTIONS.includes(value) ? value : "system"
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, preference.value)
    }
    applyTheme(preference.value)
  }

  function hydratePreference() {
    if (!import.meta.client) return
    const stored = localStorage.getItem(STORAGE_KEY) as ThemePreference | null
    preference.value = stored && OPTIONS.includes(stored) ? stored : "system"
    applyTheme(preference.value)
  }

  return {
    preference,
    options: OPTIONS,
    setPreference,
    hydratePreference,
  }
}
