export function extractApiError(err: any, fallback: string): string {
  return err?.data?.detail || err?.data?.message || err?.data?.statusMessage || err?.message || fallback
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
