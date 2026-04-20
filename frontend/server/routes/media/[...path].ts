import { createError, getHeader, setHeader } from "h3";

export default defineEventHandler(async (event) => {
  const path = event.context.params?.path;
  if (!path) {
    throw createError({ statusCode: 404, statusMessage: "Not found" });
  }

  const config = useRuntimeConfig(event);
  const upstream = `${config.backendBase}/media/${path}`;
  const response = await fetch(upstream, {
    headers: {
      ...(getHeader(event, "if-none-match") ? { "if-none-match": getHeader(event, "if-none-match")! } : {}),
      ...(getHeader(event, "if-modified-since") ? { "if-modified-since": getHeader(event, "if-modified-since")! } : {}),
    },
  });

  if (response.status === 404) {
    throw createError({ statusCode: 404, statusMessage: "Not found" });
  }

  if (!response.ok || !response.body) {
    throw createError({
      statusCode: response.status,
      statusMessage: response.statusText || "Media proxy failed",
    });
  }

  const passHeaders = ["content-type", "content-length", "cache-control", "etag", "last-modified"];
  for (const headerName of passHeaders) {
    const value = response.headers.get(headerName);
    if (value) setHeader(event, headerName, value);
  }

  return response.body;
});
