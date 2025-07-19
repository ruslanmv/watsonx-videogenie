# Metrics‑Action –  IBM Cloud Functions Usage Beacon

`metrics-action/` is a **single‑file serverless function** that records basic
front‑end telemetry for VideoGenie.  
Every browser hits this endpoint after a video render completes, passing
latency numbers and browser info.  
The action fans the data out to **Instana** (for dashboards / alerts) and
writes a local `/tmp/metrics.log` line that Log Analysis collects.

---

## Why a Cloud Function?

* **Zero pods, zero idle cost** – runs for ~30 ms per call.
* Built‑in **auto‑scale** to thousands of invocations per second.
* Easy IAM scopes: action key only needs `functions.invoke` and
  `instana.ingest`.

---

## Directory tree

```

metrics-action/
└── index.ts    # the entire function

````

---

## Full source (`index.ts`)

```ts
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
````

---

## Deploy once – then forget

```bash
# zip + upload in one go
ibmcloud fn action create metrics-action metrics-action/index.ts \
  --kind nodejs:20 \
  --memory 128 \
  --web true \
  --param defaultEventSource videogenie-spa \
  -p INSTANA_INGEST "$INSTANA_KEY"
```

The CLI prints a **web‑action URL** like
`https://<namespace>.functions.appdomain.cloud/api/v1/web/default/metrics-action`.

Add that URL to the SPA’s `.env`:

```ini
VITE_METRICS_URL=https://<namespace>.functions.appdomain.cloud/…/metrics-action
```

---

## Local test

```bash
curl -XPOST "$VITE_METRICS_URL" \
  -H "Content-Type: application/json" \
  -d '{"event":"render_complete","jobId":"test","latencyMs":123,"gpuSeconds":4,"browser":"curl"}' \
  -i
# → 204 No Content
```

Check Instana or Log Analysis after a few seconds – you should see the
ingested line.

---

## Failure modes

* **204 but nothing in Instana** – ensure the `INSTANA_INGEST` key is
  scoped to “logs ingestion” and copied verbatim into the action
  environment.
* **413 body too large** – SPA must stay under 32 KB; send only what you
  need (jobId, numbers, UA).
* No `/tmp/metrics.log` in Log Analysis – confirm that the LogDNA agent
  is configured to scrape `/tmp/*.log` inside Cloud Functions containers
  (default in IBM Cloud).

That’s it – a maintenance‑free telemetry sink for the entire
VideoGenie front‑end.


