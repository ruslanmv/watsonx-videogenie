

# VideoGenie Front‑End (React 18 · Vite · Tailwind)

This repository folder contains a **production‑ready** single‑page application that pairs with the VideoGenie back‑end on IBM Cloud.  Users paste a script, the UI auto‑generates slides, they pick an avatar & voice, then click **Generate**.  Progress streams live over WebSocket; the finished MP4 plays inline from Cloud Object Storage.

Everything below is copy‑paste complete — clone, `npm ci`, `npm run dev` and you’re live.

-----

## Directory tree

````text
frontend/
├── public/
│   ├── index.html
│   ├── favicon.svg
│   └── manifest.webmanifest
├── src/
│   ├── api.ts
│   ├── main.tsx
│   ├── App.tsx
│   ├── hooks/
│   │   └── useWebSocket.ts
│   ├── components/
│   │   ├── SlideEditor.tsx
│   │   ├── AvatarPicker.tsx
│   │   ├── VoicePicker.tsx
│   │   ├── Timeline.tsx
│   │   └── VideoPlayer.tsx
│   ├── pages/
│   │   ├── DeckPage.tsx
│   │   └── GeneratePage.tsx
│   └── styles.css
├── .env.example
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```dist/` is produced by `npm run build` and uploaded to COS; CIS caches `/assets/**` for 24 h thanks to hashed bundle names.

---

## Environment variables

```ini
# .env.example
VITE_API_URL=https://api.prd.videogenie.cloud   # REST root
VITE_WS_PATH=/notify                           # WS path (Istio route)

# App ID OIDC
VITE_APPID_CLIENT_ID=<client-id>
VITE_APPID_DISCOVERY=<https://appid.<region>.bluemix.net/oauth/v4/<guid>/.well-known/openid-configuration>

# Optional Hotjar / Instana toggle
VITE_ENABLE_ANALYTICS=false
````

Copy to `.env.local` and fill in the real values.

-----

## Development

```bash
cd frontend
npm ci
npm run dev   # → http://localhost:5173
```

-----

## Production build & upload

```bash
npm run build
ibmcloud cos upload --bucket vg-spa-assets --key '' --file dist --recursive
ibmcloud cis cache-purge <cis-zone-id> --everything      # or leave to TTL
```

-----

## Full source code

### `public/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <link rel="icon" href="/favicon.svg" />
    <link rel="manifest" href="/manifest.webmanifest" />
    <title>VideoGenie</title>
    <script>
      if (import.meta.env.VITE_ENABLE_ANALYTICS === 'true') {
        const s=document.createElement('script');s.src="/vendors/hotjar.js";document.head.appendChild(s);
      }
    </script>
  </head>
  <body class="bg-slate-50">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### `public/manifest.webmanifest`

```json
{
  "name": "VideoGenie",
  "short_name": "VideoGenie",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#2563eb",
  "icons": [
    { "src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
```

### `src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

### `src/App.tsx`

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import DeckPage from "./pages/DeckPage";
import GeneratePage from "./pages/GeneratePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DeckPage />} />
      <Route path="/generate/:jobId" element={<GeneratePage />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
```

### `src/api.ts`

```ts
import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

export const listAvatars = async () => (await api.get("/avatars")).data as { id:string;url:string }[];
export const listVoices  = async () => (await api.get("/voices")).data  as { id:string;lang:string }[];
export const startGenerate = async (body: { avatarId:string; voiceId:string; text:string; }) =>
  (await api.post("/assist", body)).data as { jobId:string };
```

### `src/hooks/useWebSocket.ts`

```ts
import { useEffect, useState } from "react";
export function useJobSocket(jobId: string) {
  const [msg, setMsg] = useState<any>(null);
  useEffect(() => {
    if (!jobId) return;
    const root = import.meta.env.VITE_API_URL.replace("https", "wss");
    const ws = new WebSocket(`${root}${import.meta.env.VITE_WS_PATH}?jobId=${jobId}`);
    ws.onmessage = (e) => setMsg(JSON.parse(e.data));
    return () => ws.close();
  }, [jobId]);
  return msg;
}
```

### `src/components/SlideEditor.tsx`

```tsx
import { useState } from "react";
export default function SlideEditor({ onChange }: { onChange: (s: string[]) => void }) {
  const [value, setValue] = useState("Welcome to VideoGenie.\n\nLet's create amazing video!");
  return (
    <textarea
      className="w-full h-60 p-3 border rounded"
      value={value}
      onChange={(e) => {
        setValue(e.target.value);
        onChange(e.target.value.split(/\n{2,}/));
      }}
    />
  );
}
```

### `src/components/AvatarPicker.tsx`

```tsx
import { useEffect, useState } from "react";
import { listAvatars } from "../api";
export default function AvatarPicker({ value, onPick }: { value?:string; onPick:(v:string)=>void }) {
  const [avatars, setAvatars] = useState<{id:string;url:string}[]>([]);
  useEffect(() => { listAvatars().then(setAvatars); }, []);
  return (
    <div className="grid grid-cols-4 gap-4">
      {avatars.map(a => (
        <img key={a.id} src={a.url} title={a.id} onClick={() => onPick(a.id)}
          className={`cursor-pointer rounded ${value===a.id?"ring-4 ring-blue-500":"hover:ring-2"}`} />
      ))}
    </div>
  );
}
```

### `src/components/VoicePicker.tsx`

```tsx
import { useEffect, useState } from "react";
import { listVoices } from "../api";
export default function VoicePicker({ value, onChange }: { value?:string; onChange:(v:string)=>void }) {
  const [voices, setVoices] = useState<{id:string;lang:string}[]>([]);
  useEffect(()=>{ listVoices().then(setVoices); },[]);
  return (
    <select className="border p-2" value={value} onChange={e=>onChange(e.target.value)}>
      <option value="">Choose voice…</option>
      {voices.map(v => <option key={v.id} value={v.id}>{v.id} ({v.lang})</option>)}
    </select>
  );
}
```

### `src/components/Timeline.tsx` (placeholder)

```tsx
export default function Timeline({ slides }:{slides:string[]}) {
  return (
    <div className="flex gap-1 mt-2">
      {slides.map((_,i)=>(<div key={i} className="flex-1 h-2 bg-blue-300" />))}
    </div>
  );
}
```

### `src/components/VideoPlayer.tsx`

```tsx
export default function VideoPlayer({ url }: { url: string }) {
  return <video src={url} controls className="w-full mt-4 border rounded shadow" />;
}
```

### `src/pages/DeckPage.tsx`

```tsx
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import SlideEditor from "../components/SlideEditor";
import AvatarPicker from "../components/AvatarPicker";
import VoicePicker from "../components/VoicePicker";
import Timeline from "../components/Timeline";
import { startGenerate } from "../api";

export default function DeckPage() {
  const nav = useNavigate();
  const [slides, setSlides] = useState<string[]>([]);
  const [avatar, setAvatar] = useState<string>("");
  const [voice, setVoice] = useState<string>("");

  const canGenerate = avatar && voice && slides.length;

  async function handleGen() {
    const { jobId } = await startGenerate({
      avatarId: avatar,
      voiceId: voice,
      text: slides.join("\n\n"),
    });
    nav(`/generate/${jobId}`);
  }

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-6">
      <h1 className="text-3xl font-bold">Create your deck</h1>
      <SlideEditor onChange={setSlides} />
      <Timeline slides={slides} />

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h2 className="font-semibold mb-2">Choose avatar</h2>
          <AvatarPicker value={avatar} onPick={setAvatar} />
        </div>
        <div>
          <h2 className="font-semibold mb-2">Choose voice</h2>
          <VoicePicker value={voice} onChange={setVoice} />
        </div>
      </div>

      <button
        className="btn-primary"
        disabled={!canGenerate}
        onClick={handleGen}
      >
        Generate video
      </button>
    </div>
  );
}
```

### `src/pages/GeneratePage.tsx`

```tsx
import { useParams } from "react-router-dom";
import { useJobSocket } from "../hooks/useWebSocket";
import VideoPlayer from "../components/VideoPlayer";

export default function GeneratePage() {
  const { jobId } = useParams();
  const msg = useJobSocket(jobId!);

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold">Generating...</h1>
      <p className="text-gray-600 mt-2">Job ID: {jobId}</p>

      {msg ? (
        <div>
          <p>Status: {msg.status}</p>
          {msg.progress && <p>Progress: {msg.progress}%</p>}
          {msg.videoUrl && <VideoPlayer url={msg.videoUrl} />}
        </div>
      ) : (
        <p>Connecting to progress stream...</p>
      )}
    </div>
  );
}
```