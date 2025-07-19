import { useParams, Link } from "react-router-dom";
import { useJobSocket } from "../hooks/useWebSocket";
import VideoPlayer from "../components/VideoPlayer";

export default function GeneratePage() {
  const { jobId } = useParams<{ jobId: string }>();
  const message = useJobSocket(jobId!);

  const status = message?.status || "Initializing job...";
  const videoUrl = message?.status === "complete" ? message.url : null;

  return (
    <div className="max-w-4xl mx-auto p-8 text-center">
      <h1 className="text-3xl font-bold mb-4">Generating Your Video</h1>
      <p className="text-lg mb-2 text-gray-600">Job ID: {jobId}</p>

      <div className="p-6 bg-gray-100 rounded-lg shadow-inner my-6">
        <p className="font-mono text-xl animate-pulse">{status}</p>
      </div>

      {videoUrl && (
        <div>
          <h2 className="text-2xl font-semibold text-green-600 mb-4">Complete!</h2>
          <VideoPlayer url={videoUrl} />
        </div>
      )}

      <Link to="/" className="inline-block mt-8 text-blue-600 hover:underline">
        &larr; Back to editor
      </Link>
    </div>
  );
}
