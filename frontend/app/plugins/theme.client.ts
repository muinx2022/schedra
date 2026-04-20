export default defineNuxtPlugin(() => {
  const theme = useThemePreference()
  theme.hydratePreference()
})
