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
