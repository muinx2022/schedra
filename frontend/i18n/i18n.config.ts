import en from "./locales/en.json"
import vi from "./locales/vi.json"

export default defineI18nConfig(() => ({
  legacy: false,
  locale: "en",
  fallbackLocale: {
    "en-US": ["en"],
    "vi-VN": ["vi"],
    default: ["en"],
  },
  missingWarn: false,
  fallbackWarn: false,
  messages: {
    en,
    vi,
    "en-US": en,
    "vi-VN": vi,
  },
}))
