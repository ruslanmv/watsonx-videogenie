# Metrics-Action – Serverless Usage Beacon

Welcome to the `Metrics-Action` microservice, the most lightweight component in the VideoGenie stack. This service is a single, serverless **IBM Cloud Function** written in TypeScript. Its sole purpose is to act as a highly-efficient, zero-maintenance telemetry sink.

Whenever a video rendering process is completed in a user's browser, the front-end application sends a small payload of metrics to this function. The function then forwards this data to both **IBM Cloud Log Analysis** and **Instana** for monitoring, dashboarding, and alerting, before returning an empty response.

This serverless approach is ideal for this use case, as it requires no pods, no scaling configuration, and no ongoing maintenance. You pay only for the few milliseconds of execution time per invocation.

-----

## ✨ Core Functionality

  * **Stateless & Serverless:** Runs as an on-demand IBM Cloud Function, eliminating the need for dedicated compute resources.
  * **Dual Telemetry Forwarding:** Pushes metrics to two separate observability platforms:
      * **Log Analysis:** Writes a simple log line for long-term storage and querying.
      * **Instana:** Forwards the full JSON payload for rich application performance monitoring (APM) and dashboarding.
  * **Asynchronous & Non-Blocking:** The function is designed to be "fire-and-forget," immediately returning a `204 No Content` response to the client so as not to block the user's browser.
  * **Cost-Effective:** The pay-per-invocation model ensures you only incur costs for actual usage, making it extremely economical for collecting telemetry data.

-----

## 📁 Directory Structure

The service is intentionally simple, consisting of just a single file.

```text
metrics-action/
└── index.ts    # The one-file Cloud Function
```

-----

## 1\. Source Code (`index.ts`)

The entire logic is contained within this TypeScript file.

```ts
/**
 * Cloud Functions action that records front-end metrics.
 * Expected JSON body from SPA:
 * {
 * "event": "render_complete",
 * "jobId": "uuid",
 * "latencyMs": 9342,
 * "gpuSeconds": 47,
 * "browser": "Chrome/126"
 * }
 */
import { writeFileSync } from "fs";
import https from "https";

// Instana RUM ingestion key (set as env var in action)
const INSTANA_KEY = process.env.INSTANA_INGEST || "";

async function pushInstana(payload: any) {
  if (!INSTANA_KEY) return;
  const postData = JSON.stringify(payload);
  const req = https.request(
    {
      hostname: "ingress-red-saas.instana.io",
      path: `/api/logs?immediate`,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-instana-key": INSTANA_KEY,
        "Content-Length": Buffer.byteLength(postData),
      },
    },
    (res) => res.resume(),
  );
  req.on("error", console.error);
  req.write(postData);
  req.end();
}

export async function main(params: any) {
  try {
    const body =
      typeof params.__ow_body === "string"
        ? JSON.parse(Buffer.from(params.__ow_body, "base64").toString())
        : params;

    // Write a quick log line (picked up by Log Analysis side-car)
    const line = `${new Date().toISOString()} ${body.event} ${body.jobId} ` +
                 `${body.latencyMs}ms ${body.gpuSeconds}s ${body.browser}\n`;
    writeFileSync("/tmp/metrics.log", line, { flag: "a" });

    // Push to Instana asynchronously (fire-and-forget)
    pushInstana(body);
    return { statusCode: 204 };
  } catch (e: any) {
    console.error(e);
    return { statusCode: 400, body: e.message };
  }
}
```

**Note:** IBM Cloud Functions can directly execute TypeScript files for the `nodejs:20` kind. The platform automatically transpiles the code with `esbuild` behind the scenes.

-----

## 🚀 Deployment

This is a one-time setup. The CI/CD pipeline does not need to touch this function unless the source code itself changes.

1.  **Deploy the Cloud Function:**
    Use the `ibmcloud fn` CLI to create the action. This command also exposes it as a web action and securely passes your Instana ingestion key as a parameter.

    ```bash
    ibmcloud fn action create metrics-action metrics-action/index.ts \
      --kind nodejs:20 --web true \
      --param eventSource video_genie \
      --annotation final true \
      -p INSTANA_INGEST "$INSTANA_KEY"
    ```

2.  **Get the Public URL:**
    Retrieve the web-accessible URL for the function. This URL should be added to your front-end application's `.env` file as `VITE_METRICS_URL`.

    ```bash
    echo "https://$(ibmcloud fn namespace get --field host)/api/v1/web/default/metrics-action"
    ```

-----

## ⚙️ Front-End Integration

The front-end application calls this function using a simple `fetch` request after a video has been successfully rendered.

```javascript
fetch(import.meta.env.VITE_METRICS_URL, {
  method: "POST",
  body: JSON.stringify({
    event: "render_complete",
    jobId,
    latencyMs,
    gpuSeconds,
    browser: navigator.userAgent,
  }),
});
```

With this simple setup, you have a complete, stateless, and zero-maintenance telemetry sink that feeds both Instana for APM and Log Analysis for dashboards and SLA alerts.