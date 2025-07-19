import { useEffect, useState } from "react";
import { listVoices } from "../api";

export default function VoicePicker({ value, onChange }: { value?:string; onChange:(v:string)=>void }) {
  const [voices, setVoices] = useState<{id:string;lang:string}[]>([]);
  useEffect(()=>{ listVoices().then(setVoices); },[]);
  return (
    <select className="border p-2 rounded w-full" value={value} onChange={e=>onChange(e.target.value)}>
      <option value="">Choose voice…</option>
      {voices.map(v => <option key={v.id} value={v.id}>{v.id} ({v.lang})</option>)}
    </select>
  );
}
