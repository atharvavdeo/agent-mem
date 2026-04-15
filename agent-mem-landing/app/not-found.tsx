import Link from "next/link";

export default function NotFound() {
  return (
    <div className="relative flex h-screen w-full flex-col items-center justify-center overflow-hidden bg-[#2A0505] font-sans selection:bg-orange-500/30 text-white">
      {/* Immersive 3D-like text background filling the screen */}
      <div className="absolute inset-0 flex items-center justify-center mix-blend-screen pointer-events-none mb-10 overflow-hidden">
        <h1 className="text-[120vw] md:text-[60vw] font-black leading-none tracking-tighter text-transparent bg-clip-text bg-linear-to-br from-yellow-300 via-orange-500 to-red-600 opacity-90 pb-[10vh] drop-shadow-[0_0_80px_rgba(255,100,0,0.4)] whitespace-nowrap -ml-[20%]">
          4<span className="relative">0</span>4
        </h1>
      </div>

      {/* Foreground Content inside the '0' area vertically/horizontally centered */}
      <div className="relative z-10 flex h-full flex-col items-center pt-[25vh] md:pt-[10%] drop-shadow-md">
        <p className="text-center font-bold text-[#FFEDA0] sm:text-lg md:text-xl xl:text-2xl uppercase tracking-widest leading-tight whitespace-pre-wrap max-w-xs drop-shadow-[0_4px_10px_rgba(0,0,0,0.8)]">
          THE PAGE YOU<br />
          ARE LOOKING<br />
          FOR DOES NOT<br />
          EXIST<br />
        </p>
      </div>

      {/* Bottom marquee-like huge white text with the overlapping button */}
      <div className="absolute bottom-6 w-full flex flex-col items-center overflow-hidden h-[25vh] justify-end">
        {/* Very large white text matching the screenshot */}
        <h2 className="-ml-[10%] text-white text-[25vw] md:text-[18vw] font-bold tracking-tighter whitespace-nowrap leading-none opacity-100 flex items-end translate-y-16 lg:translate-y-[8vh]">
          <span className="hidden sm:inline">GE&nbsp;</span>NOT FOUND PAGE | <span className="mx-8 text-white/5">ERROR</span>
        </h2>
      </div>

      {/* Take Me Home Button matching the screenshot perfectly */}
      <div className="absolute bottom-[8%] sm:bottom-12 md:bottom-16 w-full flex justify-center z-20">
        <Link
          href="/"
          className="bg-white text-black px-5 py-2 md:px-8 md:py-3 rounded-full font-extrabold uppercase text-xs md:text-sm tracking-wider shadow-xl shadow-black/80 hover:bg-neutral-200 transition-all hover:scale-105 active:scale-95"
        >
          Take Me Home
        </Link>
      </div>
    </div>
  );
}