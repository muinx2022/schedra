function normalizeErrorValue(value: any): string {
  if (typeof value === "string") {
    const trimmed = value.trim()
    if (!trimmed) return ""

    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        return normalizeErrorValue(JSON.parse(trimmed))
      } catch {
        // Keep the original string when it is not valid JSON.
      }
    }

    return trimmed
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeErrorValue(item))
      .filter(Boolean)
      .join(" ")
      .trim()
  }

  if (!value || typeof value !== "object") {
    return ""
  }

  const prioritizedKeys = ["detail", "message", "statusMessage", "error", "non_field_errors"]
  for (const key of prioritizedKeys) {
    const nested = normalizeErrorValue(value[key])
    if (nested) return nested
  }

  const entries = Object.entries(value)
    .map(([key, nestedValue]) => {
      const nested = normalizeErrorValue(nestedValue)
      if (!nested) return ""
      return Array.isArray(nestedValue) || typeof nestedValue === "object" ? `${key}: ${nested}` : nested
    })
    .filter(Boolean)

  return entries.join(" ").trim()
}

export function extractApiError(err: any, fallback: string): string {
  const candidates = [
    err?.data,
    err?.response?._data,
    err?.response?.data,
    err?.data?.detail,
    err?.data?.message,
    err?.data?.statusMessage,
    err?.message,
  ]

  for (const candidate of candidates) {
    const message = normalizeErrorValue(candidate)
    if (message) return message
  }

  return fallback
}

export async function apiFetch<T>(path: string, options?: Parameters<typeof $fetch<T>>[1]) {
  const normalizedPath = path.endsWith("/") ? path : `${path}/`

  // In SSR, forward the browser's cookies to the BFF so Django can verify the session
  const ssrHeaders: Record<string, string> = {}
  if (import.meta.server) {
    const { cookie } = useRequestHeaders(["cookie"])
    if (cookie) ssrHeaders.cookie = cookie
  }

  return $fetch<T>(`/api/bff${normalizedPath}`, {
    credentials: "include",
    retry: 0,
    timeout: 8000,
    headers: ssrHeaders,
    ...options,
  })
}
