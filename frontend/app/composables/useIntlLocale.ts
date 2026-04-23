export function useIntlLocale() {
  const { locale } = useI18n()
  return computed(() => (locale.value === "vi" ? "vi-VN" : "en-US"))
}

