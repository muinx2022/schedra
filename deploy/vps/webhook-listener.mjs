import { createServer } from "node:http";
import { spawn } from "node:child_process";

const allowedServices = new Set(["api", "web"]);
const host = process.env.DEPLOY_HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.DEPLOY_PORT ?? "8787", 10);
const token = process.env.DEPLOY_WEBHOOK_TOKEN;
const deployScript = process.env.DEPLOY_SCRIPT;

if (!token) throw new Error("DEPLOY_WEBHOOK_TOKEN is required");
if (!deployScript) throw new Error("DEPLOY_SCRIPT is required");

let deploymentInProgress = false;

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;

    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > 64 * 1024) {
        reject(new Error("Payload too large"));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });

    request.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8");
        resolve(raw ? JSON.parse(raw) : {});
      } catch (error) {
        reject(error);
      }
    });

    request.on("error", reject);
  });
}

function normalizePayload(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Payload must be a JSON object");
  }

  const { ref, sha, services } = payload;

  if (typeof ref !== "string" || !ref) throw new Error("ref must be a non-empty string");
  if (typeof sha !== "string" || !sha) throw new Error("sha must be a non-empty string");
  if (!Array.isArray(services)) throw new Error("services must be an array");

  const uniqueServices = [...new Set(services.filter((service) => typeof service === "string"))];
  if (uniqueServices.some((service) => !allowedServices.has(service))) {
    throw new Error("services contains an unsupported service");
  }

  return { ref, sha, services: uniqueServices };
}

function runDeploy({ ref, sha, services }) {
  return new Promise((resolve, reject) => {
    const child = spawn("bash", [deployScript, sha, ...services], {
      env: {
        ...process.env,
        DEPLOY_REF: ref,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });

    child.stdout.on("data", (chunk) => process.stdout.write(chunk.toString()));
    child.stderr.on("data", (chunk) => process.stderr.write(chunk.toString()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve(undefined);
        return;
      }
      reject(new Error(`Deploy script exited with code ${code}`));
    });
  });
}

const server = createServer(async (request, response) => {
  let deploymentStarted = false;

  try {
    if (request.method === "GET" && request.url === "/health") {
      sendJson(response, 200, { ok: true, busy: deploymentInProgress });
      return;
    }

    if (request.method !== "POST" || request.url !== "/deploy") {
      sendJson(response, 404, { ok: false, error: "Not found" });
      return;
    }

    if (request.headers["x-deploy-token"] !== token) {
      sendJson(response, 401, { ok: false, error: "Unauthorized" });
      return;
    }

    const payload = normalizePayload(await readJsonBody(request));

    if (payload.services.length === 0) {
      sendJson(response, 202, { ok: true, skipped: true });
      return;
    }

    if (deploymentInProgress) {
      sendJson(response, 409, { ok: false, error: "Deployment already in progress" });
      return;
    }

    deploymentInProgress = true;
    deploymentStarted = true;
    console.log(`[deploy] start ref=${payload.ref} sha=${payload.sha} services=${payload.services.join(",")}`);

    await runDeploy(payload);

    console.log(`[deploy] done sha=${payload.sha}`);
    sendJson(response, 200, { ok: true, sha: payload.sha, services: payload.services });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error(`[deploy] failed: ${message}`);
    if (!response.headersSent) {
      sendJson(response, 400, { ok: false, error: message });
    }
  } finally {
    if (deploymentStarted) {
      deploymentInProgress = false;
    }
  }
});

server.listen(port, host, () => {
  console.log(`Deploy listener running on http://${host}:${port}`);
});
