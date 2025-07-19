/**
 * IBM Cloud Functions action recording render‑complete metrics.
 *
 * Example JSON payload sent by the React SPA:
 * {
 *   "event": "render_complete",
 *   "jobId": "b2c8599b-3e6b",
 *   "latencyMs": 9342,
 *   "gpuSeconds": 47,
 *   "browser": "Chrome/126"
 * }
 */
import { writeFileSync } from "fs";
import https from "https";

const INSTANA_KEY = process.env.INSTANA_INGEST || "";

async function pushInstana(payload: Record<string, unknown>) {
  if (!INSTANA_KEY) return;
  const body = JSON.stringify(payload);

  const req = https.request(
    {
      hostname: "ingress-red-saas.instana.io",
      path: "/api/logs?immediate",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-instana-key": INSTANA_KEY,
        "Content-Length": Buffer.byteLength(body),
      },
    },
    (res) => res.resume(), // ignore response body
  );
  req.on("error", console.error);
  req.write(body);
  req.end();
}

// Cloud Functions action entry‑point
export async function main(params: any) {
  try {
    // IBM CF passes body base64‑encoded under __ow_body
    const body =
      typeof params.__ow_body === "string"
        ? JSON.parse(Buffer.from(params.__ow_body, "base64").toString())
        : params;

    // quick sanity check
    if (!body?.event || !body?.jobId) {
      return { statusCode: 400, body: "missing event or jobId" };
    }

    // 1 · Write a lightweight log line → Log Analysis
    const line =
      `${new Date().toISOString()} ${body.event} ${body.jobId} ` +
      `${body.latencyMs}ms ${body.gpuSeconds}s ${body.browser}\n`;
    writeFileSync("/tmp/metrics.log", line, { flag: "a" });

    // 2 · Async push to Instana
    pushInstana(body);

    // no content needed
    return { statusCode: 204 };
  } catch (err: any) {
    console.error(err);
    return { statusCode: 500, body: err.message };
  }
}