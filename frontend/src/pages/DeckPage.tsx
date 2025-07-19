import { useNavigate } from "react-router-dom";
import { useState } from "react";
import SlideEditor from "../components/SlideEditor";
import AvatarPicker from "../components/AvatarPicker";
import VoicePicker from "../components/VoicePicker";
import Timeline from "../components/Timeline";
import { startGenerate } from "../api";

export default function DeckPage() {
  const nav = useNavigate();
  const [slides, setSlides] = useState<string[]>(["Welcome to VideoGenie.", "Let's create amazing video!"]);
  const [avatar, setAvatar] = useState<string>("");
  const [voice, setVoice] = useState<string>("");

  const canGenerate = avatar && voice && slides.length > 0 && slides.join("").trim() !== "";

  async function handleGen() {
    if (!canGenerate) return;
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

      <div className="grid md:grid-cols-2 gap-6 pt-4">
        <div>
          <h2 className="font-semibold mb-2 text-xl">1. Choose your avatar</h2>
          <AvatarPicker value={avatar} onPick={setAvatar} />
        </div>
        <div>
          <h2 className="font-semibold mb-2 text-xl">2. Choose your voice</h2>
          <VoicePicker value={voice} onChange={setVoice} />
        </div>
      </div>

      <div className="pt-6 text-center">
        <button
          className="btn-primary w-full md:w-auto text-lg"
          disabled={!canGenerate}
          onClick={handleGen}
        >
          Generate video
        </button>
      </div>
    </div>
  );
}
