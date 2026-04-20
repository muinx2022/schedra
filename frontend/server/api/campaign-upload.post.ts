import { getHeader } from "h3";

import { buildBackendHeaders, mirrorBackendCookies } from "../utils/backend";

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event);
  const contentType = getHeader(event, "content-type");
  const contentLength = getHeader(event, "content-length");

  const response = await fetch(`${config.backendBase}/api/campaigns/`, {
    method: "POST",
    headers: {
      ...buildBackendHeaders(event),
      ...(contentType ? { "content-type": contentType } : {}),
      ...(contentLength ? { "content-length": contentLength } : {}),
    },
    body: event.node.req,
    duplex: "half",
  });

  mirrorBackendCookies(event, response);
  const text = await response.text();
  if (!response.ok) {
    throw createError({ statusCode: response.status, message: text || response.statusText });
  }
  return text ? JSON.parse(text) : {};
});

