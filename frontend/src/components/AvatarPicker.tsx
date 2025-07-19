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
