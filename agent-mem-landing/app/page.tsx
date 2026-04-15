import { ArrowRight, TerminalSquare } from 'lucide-react';
import Image from 'next/image';
import Hero from '../components/Hero';
import Features from '../components/Features';

export default function Home() {
  return (
    <main className="relative isolate overflow-hidden bg-black text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(251,146,60,0.10),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(34,211,238,0.08),transparent_30%),linear-gradient(to_bottom,#050505,#0a0a0a_45%,#050505_100%)]" />
      <div className="relative z-10">
        <Hero />
        <Features />

        <section id="install" className="mx-auto max-w-6xl px-6 pb-24 pt-10 sm:pt-16">
          <div className="group relative overflow-hidden rounded-4xl border border-white/10 bg-white/4 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-orange-400/35 hover:bg-white/6 md:p-10">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(251,146,60,0.16),transparent_35%),radial-gradient(circle_at_bottom_left,rgba(34,211,238,0.10),transparent_32%)]" />
            <div className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-orange-400/60 to-transparent" />
            <div className="relative z-10 grid gap-8 md:grid-cols-[1.15fr_0.85fr] md:items-center">
              <div>
                <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.35em] text-white/60 transition-colors duration-300 group-hover:border-orange-400/25 group-hover:bg-white/10 group-hover:text-white">
                  <Image src="/logo.png" alt="agent-mem logo" width={18} height={18} className="h-4 w-4 rounded-sm object-cover" />
                  Ship faster
                </div>
                <h2 className="mt-5 max-w-xl text-3xl font-semibold tracking-tight text-white md:text-5xl">
                  Start in 20 seconds without context loss.
                </h2>
                <p className="mt-4 max-w-xl text-base leading-7 text-white/70 md:text-lg">
                  One install, one watch command, and a durable memory layer that keeps your agent oriented.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/45">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Private</span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Fast</span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Local</span>
                </div>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <a href="https://github.com/atharvavdeo/agent-mem" target="_blank" className="group inline-flex items-center justify-center gap-2 rounded-full bg-linear-to-r from-orange-500 via-amber-400 to-yellow-300 px-6 py-3 font-semibold text-black shadow-[0_18px_50px_rgba(251,146,60,0.25)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_22px_60px_rgba(251,146,60,0.35)]">
                    Install now
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
                  </a>
                  <a href="https://pypi.org/project/easy-agent-mem/" target="_blank" className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-6 py-3 font-semibold text-white/85 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/25 hover:bg-white/10 hover:text-white">
                    Read docs
                  </a>
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-black/40 p-5 font-mono text-sm shadow-inner transition-all duration-300 hover:border-orange-400/30 hover:bg-black/55 hover:shadow-[0_20px_60px_rgba(251,146,60,0.14)]">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-white/35">
                  <span>Quick start</span>
                  <TerminalSquare className="h-4 w-4 text-orange-300" />
                </div>
                <div className="mt-4 space-y-3">
                  <div className="rounded-xl border border-white/10 bg-white/4 px-4 py-3 text-white/80 transition-colors hover:border-orange-400/30 hover:bg-white/8">
                    pip install easy-agent-mem
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/4 px-4 py-3 text-white/80 transition-colors hover:border-orange-400/30 hover:bg-white/8">
                    agent-mem watch
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-white/3 px-4 py-3 text-[11px] uppercase tracking-[0.3em] text-white/40 transition-colors hover:border-orange-400/25 hover:bg-white/6">
                  <span>Status</span>
                  <span className="text-green-400">ready</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
