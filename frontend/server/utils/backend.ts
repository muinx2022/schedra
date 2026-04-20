import type { H3Event } from "h3";
import { appendResponseHeader, getCookie, getHeader, getMethod, readBody } from "h3";

function agentLog(hypothesisId: string, location: string, message: string, data: Record<string, any>) {
  // #region agent log
  fetch("http://127.0.0.1:7303/ingest/1227dba4-b43d-4906-b417-ee17d9ea5438", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "fd08c2" },
    body: JSON.stringify({
      sessionId: "fd08c2",
      runId: "pre-fix",
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
}

export function buildBackendHeaders(event: H3Event) {
  const cookie = getHeader(event, "cookie");
  const csrfToken = getCookie(event, "csrftoken");
  const headers: Record<string, string> = { accept: "application/json" };
  if (cookie) headers.cookie = cookie;
  if (csrfToken) headers["x-csrftoken"] = csrfToken;
  return headers;
}

export function mirrorBackendCookies(event: H3Event, response: Response) {
  // getSetCookie() is Node 18.14.1+ — fall back to forEach for older runtimes
  const setCookies: string[] = response.headers.getSetCookie?.() ?? []
  if (setCookies.length > 0) {
    for (const c of setCookies) appendResponseHeader(event, "set-cookie", c)
    return
  }
  response.headers.forEach((_value: string, name: string) => {
    if (name.toLowerCase() === "set-cookie") {
      const raw = response.headers.get(name)
      if (raw) appendResponseHeader(event, "set-cookie", raw)
    }
  })
}

export async function proxyToBackend(event: H3Event, path: string) {
  const config = useRuntimeConfig(event);
  const method = getMethod(event);
  const body = ["POST", "PUT", "PATCH", "DELETE"].includes(method) ? await readBody(event) : undefined;
  const headers = buildBackendHeaders(event);
  agentLog("F", "frontend/server/utils/backend.ts:proxyToBackend", "Proxy request prepared", {
    path,
    method,
    backendBase: config.backendBase,
    hasCookieHeader: Boolean((headers as any).cookie),
    cookieHeaderLength: ((headers as any).cookie || "").length,
    hasCsrfCookie: Boolean(getCookie(event, "csrftoken")),
  });

  const response = await fetch(`${config.backendBase}${path}`, {
    method,
    headers: {
      ...headers,
      ...(body ? { "content-type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  mirrorBackendCookies(event, response);

  const text = await response.text();
  const contentType = response.headers.get("content-type") || "";
  agentLog("G", "frontend/server/utils/backend.ts:proxyToBackend", "Proxy response received", {
    path,
    status: response.status,
    ok: response.ok,
    contentType,
    bodySnippet: (text || "").slice(0, 200),
  });
  if (!response.ok) {
    throw createError({
      statusCode: response.status,
      message: text || response.statusText,
    });
  }
  if (contentType.includes("application/json")) {
    return text ? JSON.parse(text) : {};
  }
  return { ok: true, text };
}
