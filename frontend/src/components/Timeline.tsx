export default function Timeline({ slides }:{slides:string[]}) {
  return (
    <div className="flex gap-1 mt-2">
      {slides.map((_,i)=>(<div key={i} className="flex-1 h-2 bg-blue-300 rounded-full" />))}
    </div>
  );
}
