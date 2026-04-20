import { proxyToBackend } from "../../utils/backend";

export default defineEventHandler(async (event) => {
  const rawPath = getRouterParam(event, "path") || "";
  const path = rawPath.endsWith("/") ? rawPath : `${rawPath}/`;
  return proxyToBackend(event, `/api/${path}`);
});

