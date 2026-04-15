 'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ArrowRight, BrainCircuit, Copy, Eye, Sparkles, Zap } from 'lucide-react';
import { GradientBackground } from './ui/paper-design-shader-background';

const features = [
  {
    name: 'Watch Mode',
    icon: Eye,
    command: 'agent-mem watch',
    description: 'Monitors file changes and captures memory automatically.',
  },
  {
    name: 'CLI Init',
    icon: Zap,
    command: 'agent-mem init',
    description: 'Bootstraps the local memory layer with one command.',
  },
  {
    name: 'Recall',
    icon: BrainCircuit,
    command: 'agent-mem recall "what did we do yesterday?"',
    description: 'Recalls durable context without retyping the backstory.',
  },
] as const;

export default function Hero() {
  const [activeTab, setActiveTab] = useState(features[0].name);

  const activeFeature = features.find((feature) => feature.name === activeTab) ?? features[0];
  const ActiveIcon = activeFeature.icon;

  return (
    <section className="relative isolate overflow-hidden px-6 pb-20 pt-28 sm:pt-32">
      <GradientBackground />
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_top,rgba(251,146,60,0.16),transparent_38%),radial-gradient(circle_at_80%_12%,rgba(34,211,238,0.08),transparent_28%),linear-gradient(to_bottom,rgba(0,0,0,0.10),rgba(0,0,0,0.86))]" />
      <div className="pointer-events-none absolute left-1/2 top-16 h-72 w-72 -translate-x-1/2 rounded-full bg-orange-500/10 blur-[120px]" />
      <div className="pointer-events-none absolute right-[-8%] top-32 h-80 w-80 rounded-full bg-cyan-400/10 blur-[140px]" />

      <div className="relative z-10 mx-auto grid w-full max-w-7xl gap-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="mb-8 inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5 hover:border-orange-400/40 hover:bg-white/10">
            <Image src="/logo.png" alt="agent-mem logo" width={32} height={32} className="h-8 w-8 rounded-md object-cover ring-1 ring-white/10" priority />
            <span className="text-xs font-medium uppercase tracking-[0.28em] text-white/70">Persistent agent memory</span>
          </div>

          <a href="https://pypi.org/project/easy-agent-mem/" target="_blank" className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2 text-sm text-white/75 backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5 hover:border-orange-400/40 hover:bg-white/10 hover:text-white">
            <Sparkles className="h-4 w-4 text-orange-300" />
            Introducing easy-agent-mem v0.5.1
          </a>

          <h1 className="max-w-4xl text-balance text-5xl font-light tracking-tight text-white sm:text-6xl md:text-7xl lg:text-8xl">
            IDE Agents Forget.<br /><strong className="font-semibold text-white">agent-mem</strong> Remembers.
          </h1>

          <p className="mt-6 max-w-2xl text-pretty text-base leading-7 text-white/75 sm:text-lg md:text-xl">
            agent-mem is a universal, self-managing persistent memory layer for AI coding assistants. Reduce context loss, minimize repetition, and manage your agent&apos;s memory locally.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3 text-[10px] font-semibold uppercase tracking-[0.32em] text-white/55 lg:justify-start">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Local</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Persistent</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 transition-colors hover:border-orange-400/30 hover:bg-white/10 hover:text-white">Low-latency</span>
          </div>

          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <a href="#install" className="group inline-flex items-center justify-center gap-2 rounded-full bg-linear-to-r from-orange-500 via-amber-400 to-yellow-300 px-6 py-3 font-semibold text-black shadow-[0_18px_50px_rgba(251,146,60,0.28)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_22px_60px_rgba(251,146,60,0.35)]">
              Start in 20 seconds
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </a>
            <a href="https://github.com/atharvavdeo/agent-mem" target="_blank" className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-6 py-3 font-semibold text-white/85 backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5 hover:border-white/25 hover:bg-white/10 hover:text-white">
              View on GitHub
            </a>
          </div>

          <p className="mt-6 text-xs uppercase tracking-[0.35em] text-white/35">
            Hover a card to preview its command
          </p>
        </div>

        <div className="relative">
          <div className="absolute inset-0 rounded-4xl bg-linear-to-br from-orange-500/15 via-transparent to-cyan-400/10 blur-3xl" />
          <div className="relative overflow-hidden rounded-4xl border border-white/10 bg-black/45 p-6 shadow-[0_24px_100px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-300 hover:border-orange-400/30 hover:bg-black/55">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.35em] text-white/35">
              <span>Active command</span>
              <button
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-white/65 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
                onClick={() => navigator.clipboard.writeText(activeFeature.command)}
                title="Copy command"
              >
                <Copy className="h-3.5 w-3.5" />
                Copy
              </button>
            </div>

            <div className="mt-5 flex items-start gap-4">
              <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-orange-300 shadow-inner">
                <ActiveIcon className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h2 className="text-2xl font-semibold tracking-tight text-white">{activeFeature.name}</h2>
                <p className="mt-2 max-w-lg text-sm leading-6 text-white/60">
                  {activeFeature.description}
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
              <p className="text-[10px] uppercase tracking-[0.32em] text-white/35">Command</p>
              <code className="mt-3 block break-all font-mono text-base text-orange-300 sm:text-lg">
                $ {activeFeature.command}
              </code>
            </div>

            <div className="mt-5 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-white/40">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2">Hover driven</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2">SVG icons</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2">No loading screen</span>
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 mx-auto mt-14 grid w-full max-w-7xl gap-5 md:grid-cols-3">
        {features.map((feature) => {
          const Icon = feature.icon;
          const isActive = activeTab === feature.name;

          return (
            <button
              key={feature.name}
              type="button"
              onMouseEnter={() => setActiveTab(feature.name)}
              onFocus={() => setActiveTab(feature.name)}
              onClick={() => setActiveTab(feature.name)}
              className={`group flex min-h-62 flex-col rounded-3xl border p-6 text-left transition-all duration-300 hover:-translate-y-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40 ${isActive ? 'border-orange-400/35 bg-white/8 shadow-[0_0_0_1px_rgba(251,146,60,0.18)]' : 'border-white/10 bg-white/4 hover:border-orange-400/25 hover:bg-white/7'}`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-black/35 text-orange-300 transition-colors group-hover:border-orange-400/25 group-hover:bg-black/45 group-hover:text-orange-200">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="text-lg font-semibold text-white">{feature.name}</h3>
                  <p className="text-xs uppercase tracking-[0.28em] text-white/35">SVG icon</p>
                </div>
              </div>

              <p className="mt-4 text-sm leading-6 text-white/60">
                {feature.description}
              </p>

              <div className="mt-auto pt-8">
                <div className="h-px w-full bg-linear-to-r from-transparent via-white/10 to-transparent" />
                <div className="mt-4 flex items-center justify-between text-[10px] uppercase tracking-[0.32em] text-white/35">
                  <span>Hover to preview</span>
                  <span className={`rounded-full border px-3 py-2 transition-colors ${isActive ? 'border-orange-400/30 bg-orange-400/10 text-orange-200' : 'border-white/10 bg-white/5 text-white/45 group-hover:border-orange-400/25 group-hover:bg-white/10 group-hover:text-white'}`}>
                    Live
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
