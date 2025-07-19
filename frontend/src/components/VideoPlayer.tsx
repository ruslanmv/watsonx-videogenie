export default function VideoPlayer({ url }: { url: string }) {
  return <video src={url} controls autoPlay className="w-full mt-4 border rounded shadow" />;
}
