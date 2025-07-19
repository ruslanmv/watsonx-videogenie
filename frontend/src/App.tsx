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
