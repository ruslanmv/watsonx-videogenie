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
