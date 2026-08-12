"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import {
  Upload,
  MessageSquare,
  Layers,
  BarChart3,
  ArrowRight,
  Search,
  BookOpen,
  Zap,
  Sparkles,
} from "lucide-react";

const FEATURES = [
  {
    icon: Upload,
    title: "Upload & Index",
    desc: "Drop a PDF. Structure-aware parsing splits it into sections and chunks, then embeds each chunk into a 2048-dim vector space for semantic retrieval.",
  },
  {
    icon: Search,
    title: "Grounded Answers",
    desc: "Ask in natural language. The system embeds your query, vector-searches candidate chunks, reranks for precision, and answers with exact section citations.",
  },
  {
    icon: Layers,
    title: "Trace Inspector",
    desc: "Every request produces a real Gantt timeline — embed, search, rerank, generate, judge — with latencies, retrieval diagnostics, and rerank movement.",
  },
  {
    icon: BarChart3,
    title: "Live Health Dashboard",
    desc: "Monitor pipeline health, retrieval quality trends, per-paper citation accuracy, reranker fallback rates, and token usage in one place.",
  },
];

const PIPELINE = [
  { label: "Embed", icon: Search },
  { label: "Search", icon: BookOpen },
  { label: "Rerank", icon: Zap },
  { label: "Generate", icon: Sparkles },
  { label: "Judge", icon: BarChart3 },
];

function AnimatedPipeline() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActive((a) => (a + 1) % PIPELINE.length), 700);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center justify-center gap-2 sm:gap-3">
      {PIPELINE.map((step, idx) => {
        const Icon = step.icon;
        const isActive = idx === active;
        const isDone = idx < active;
        return (
          <div key={step.label} className="flex items-center gap-2 sm:gap-3">
            <div
              className={`flex flex-col items-center gap-1.5 transition-all duration-500 ${
                isActive ? "scale-110" : ""
              }`}
            >
              <div
                className={`relative flex size-12 sm:size-14 items-center justify-center rounded-2xl border shadow-sm transition-colors duration-500 ${
                  isDone
                    ? "bg-charcoal-900 border-charcoal-900 text-cream-50"
                    : isActive
                      ? "bg-charcoal-900 border-charcoal-900 text-cream-50"
                      : "bg-white border-charcoal-200 text-charcoal-400"
                }`}
              >
                <Icon className="size-5" />
                {isActive && (
                  <span className="absolute -inset-1 rounded-2xl border-2 border-charcoal-700/40 animate-ping" />
                )}
              </div>
              <span
                className={`text-[10px] font-medium uppercase tracking-wider ${
                  isActive ? "text-charcoal-900" : isDone ? "text-charcoal-700" : "text-charcoal-400"
                }`}
              >
                {step.label}
              </span>
            </div>
            {idx < PIPELINE.length - 1 && (
              <div className="relative h-px w-6 sm:w-10 bg-charcoal-200 overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 bg-charcoal-800 transition-all duration-500 ${
                    isDone ? "w-full" : "w-0"
                  }`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Home() {
  const router = useRouter();

  return (
    <main className="min-h-[calc(100vh-3.5rem)]">
      <section className="mx-auto max-w-5xl px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-charcoal-200 bg-white px-3 py-1 text-[11px] font-medium text-charcoal-600 shadow-sm">
          <Sparkles className="size-3.5 text-charcoal-700" />
          Grounded answers with section citations
        </div>

        <h1 className="mt-6 font-serif text-4xl sm:text-6xl font-semibold tracking-tight text-charcoal-900">
          Ask your research papers.
          <br />
          <span className="text-charcoal-500">Get cited answers.</span>
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-base sm:text-lg leading-relaxed text-charcoal-600">
          Paper Pilot turns uploaded PDFs into a searchable research assistant.
          Ask targeted questions and receive grounded responses backed by exact
          section citations, with full pipeline tracing you can inspect.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 rounded-xl bg-charcoal-900 px-6 py-3 text-sm font-semibold text-cream-50 shadow-lg transition-all hover:bg-charcoal-800 hover:shadow-xl"
          >
            <MessageSquare className="size-4" />
            Start a conversation
            <ArrowRight className="size-4" />
          </Link>
          <Link
            href="/papers"
            className="inline-flex items-center gap-2 rounded-xl border border-charcoal-300 bg-white px-6 py-3 text-sm font-semibold text-charcoal-900 shadow-sm transition-all hover:bg-charcoal-50"
          >
            <BookOpen className="size-4" />
            Browse papers
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-16">
        <div className="rounded-3xl border border-charcoal-200 bg-cream-50 p-8 sm:p-10 shadow-sm">
          <p className="mb-8 text-center text-xs font-bold uppercase tracking-widest text-charcoal-500">
            The RAG pipeline
          </p>
          <AnimatedPipeline />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-20">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="group rounded-2xl border border-charcoal-200 bg-white p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="flex size-10 items-center justify-center rounded-xl bg-charcoal-900 text-cream-50 shadow-sm">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 text-base font-bold text-charcoal-900">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-charcoal-600">
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="rounded-3xl border border-charcoal-900 bg-charcoal-900 px-8 py-12 text-center shadow-xl">
          <h2 className="font-serif text-3xl font-semibold text-cream-50">
            Upload a paper and ask away.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-charcoal-200">
            Get started in seconds — no sign-up, no setup. Your PDFs are parsed,
            embedded, and searchable in real time.
          </p>
          <button
            onClick={() => router.push("/chat")}
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-cream-50 px-6 py-3 text-sm font-semibold text-charcoal-900 shadow-lg transition-all hover:bg-white"
          >
            <Upload className="size-4" />
            Open Paper Pilot
          </button>
        </div>
      </section>
    </main>
  );
}
