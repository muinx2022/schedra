import { createError, getCookie, getQuery, getRouterParam, sendRedirect } from "h3"

const PATH_PROVIDERS = new Set(["facebook", "instagram", "tiktok", "youtube", "pinterest"])
const SUPPORTED_LOCALES = new Set(["en", "vi"])
const DEFAULT_LOCALE = "en"

function resolveLocale(event: Parameters<typeof getCookie>[0]) {
  const locale = getCookie(event, "schedra_locale") || DEFAULT_LOCALE
  return SUPPORTED_LOCALES.has(locale) ? locale : DEFAULT_LOCALE
}

export default defineEventHandler((event) => {
  const provider = getRouterParam(event, "provider") || ""
  const locale = resolveLocale(event)

  if (!provider) {
    throw createError({ statusCode: 404, statusMessage: "Not found" })
  }

  const targetPath = PATH_PROVIDERS.has(provider)
    ? `/${locale}/app/settings/provider/${provider}`
    : `/${locale}/app/settings`

  const query = new URLSearchParams()
  const rawQuery = getQuery(event)

  for (const [key, value] of Object.entries(rawQuery)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item != null) query.append(key, String(item))
      }
      continue
    }
    if (value != null) query.set(key, String(value))
  }

  if (!PATH_PROVIDERS.has(provider)) {
    query.set("provider", provider)
  }

  const destination = query.size ? `${targetPath}?${query.toString()}` : targetPath
  return sendRedirect(event, destination)
})
