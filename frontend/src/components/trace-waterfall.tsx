"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, ArrowUpRight, ArrowDownRight, Layers, Sparkles, Search, BookOpen, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export interface TraceSpan {
  span_id?: string;
  name: string;
  duration_ms: number;
  offset_ms?: number;
  start_time_ns?: number;
  status?: string;
  attributes?: Record<string, any>;
}

interface TraceWaterfallProps {
  spans: TraceSpan[];
  totalDurationMs?: number;
}

const STEP_COLORS: Record<string, { bg: string; bar: string; badge: string }> = {
  embed: { bg: "bg-indigo-50", bar: "bg-indigo-600", badge: "bg-indigo-100 text-indigo-800" },
  vector_search: { bg: "bg-sky-50", bar: "bg-sky-600", badge: "bg-sky-100 text-sky-800" },
  rerank: { bg: "bg-amber-50", bar: "bg-amber-600", badge: "bg-amber-100 text-amber-800" },
  generate: { bg: "bg-emerald-50", bar: "bg-emerald-600", badge: "bg-emerald-100 text-emerald-800" },
  judge: { bg: "bg-purple-50", bar: "bg-purple-600", badge: "bg-purple-100 text-purple-800" },
};

const STEP_ICONS: Record<string, any> = {
  embed: Search,
  vector_search: BookOpen,
  rerank: Zap,
  generate: Sparkles,
  judge: Layers,
};

export function TraceWaterfall({ spans, totalDurationMs }: TraceWaterfallProps) {
  const [expandedSpan, setExpandedSpan] = useState<string | null>(null);

  if (!spans || spans.length === 0) {
    return <p className="text-xs text-slate-400 py-2">No span data recorded for this trace.</p>;
  }

  // Calculate timeline offsets
  let minStartNs = Infinity;
  spans.forEach((s) => {
    if (s.start_time_ns && s.start_time_ns < minStartNs) {
      minStartNs = s.start_time_ns;
    }
  });

  const processedSpans = spans.map((s, idx) => {
    let offset = s.offset_ms ?? 0;
    if (s.start_time_ns && minStartNs !== Infinity) {
      offset = Math.max(0, Math.round((s.start_time_ns - minStartNs) / 1_000_000));
    }
    return { ...s, computedOffsetMs: offset, id: s.span_id || `span-${idx}` };
  });

  const maxEndMs = totalDurationMs || Math.max(...processedSpans.map((s) => s.computedOffsetMs + s.duration_ms), 1);

  return (
    <div className="space-y-4 bg-white text-slate-900 p-4 rounded-xl shadow-xs border border-slate-200">
      {/* Header Summary Bar */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="size-4 text-slate-800" />
          <span className="text-xs font-bold text-slate-900 tracking-wide">
            Pipeline Execution Gantt Chart
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-slate-500">
          <span>{spans.length} Spans</span>
          <span>•</span>
          <span className="text-slate-900 font-bold">{maxEndMs} ms total</span>
        </div>
      </div>

      {/* Waterfall Axis Scale */}
      <div className="relative h-4 w-full flex items-center text-[10px] font-mono text-slate-400 border-b border-slate-100 pb-1">
        <span className="w-28 shrink-0 text-slate-500 font-semibold">Step Name</span>
        <div className="flex-1 flex justify-between px-1">
          <span>0ms</span>
          <span>{Math.round(maxEndMs * 0.25)}ms</span>
          <span>{Math.round(maxEndMs * 0.5)}ms</span>
          <span>{Math.round(maxEndMs * 0.75)}ms</span>
          <span>{maxEndMs}ms</span>
        </div>
      </div>

      {/* Gantt Bar Rows */}
      <div className="space-y-2">
        {processedSpans.map((span) => {
          const style = STEP_COLORS[span.name] || { bg: "bg-slate-100", bar: "bg-slate-700", badge: "bg-slate-100 text-slate-800" };
          const Icon = STEP_ICONS[span.name] || Layers;
          const leftPct = Math.min(95, Math.max(0, (span.computedOffsetMs / maxEndMs) * 100));
          const widthPct = Math.min(100 - leftPct, Math.max(2, (span.duration_ms / maxEndMs) * 100));
          const isExpanded = expandedSpan === span.id;
          const hasError = span.status === "error" || span.attributes?.finish_reason === "error";
          const hasFallback = span.attributes?.fallback === true;

          return (
            <div key={span.id} className="rounded-lg bg-slate-50 border border-slate-200 overflow-hidden transition-all">
              {/* Main Row Bar */}
              <button
                onClick={() => setExpandedSpan(isExpanded ? null : span.id)}
                className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-slate-100/80 transition-colors"
              >
                {/* Step Label */}
                <div className="w-28 shrink-0 flex items-center gap-1.5 min-w-0">
                  {isExpanded ? (
                    <ChevronDown className="size-3 text-slate-500 shrink-0" />
                  ) : (
                    <ChevronRight className="size-3 text-slate-500 shrink-0" />
                  )}
                  <Icon className="size-3.5 text-slate-700 shrink-0" />
                  <span className="text-xs font-semibold text-slate-900 truncate capitalize">
                    {span.name.replace("_", " ")}
                  </span>
                </div>

                {/* Timeline Bar Track */}
                <div className="flex-1 relative h-6 bg-slate-200/70 rounded flex items-center px-1 overflow-hidden">
                  <div
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    className={`absolute h-4 rounded transition-all duration-300 ${
                      hasError
                        ? "bg-rose-600 border border-rose-500 shadow-2xs"
                        : hasFallback
                        ? "bg-amber-500 border border-amber-400 shadow-2xs"
                        : style.bar
                    }`}
                  />
                  <span className="relative z-10 text-[10px] font-mono text-slate-700 font-bold ml-auto pr-1">
                    {span.duration_ms}ms
                  </span>
                </div>

                {/* Badges */}
                <div className="shrink-0 flex items-center gap-1">
                  {hasFallback && (
                    <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-800 bg-amber-50">
                      Rerank Fallback
                    </Badge>
                  )}
                  {hasError && (
                    <Badge variant="outline" className="text-[10px] border-rose-300 text-rose-800 bg-rose-50">
                      Error
                    </Badge>
                  )}
                  <span className="text-[10px] font-mono text-slate-500 w-12 text-right">
                    +{span.computedOffsetMs}ms
                  </span>
                </div>
              </button>

              {/* Diagnostic Details Panel */}
              {isExpanded && (
                <div className="border-t border-slate-200 bg-white p-3.5 space-y-3 text-xs">
                  {/* Reranker Movement Diagnostic Table */}
                  {span.name === "rerank" && (span.attributes?.reranked_chunks?.length ?? 0) > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
                          Reranker Movement & Promotion Diagnostics
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Top {span.attributes?.reranked_chunks?.length || 0} Chunks
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {span.attributes?.reranked_chunks?.map((chk: any, i: number) => {
                          const isPromoted = chk.rank_change > 0;
                          const isDemoted = chk.rank_change < 0;
                          return (
                            <div
                              key={chk.chunk_id || i}
                              className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs gap-2"
                            >
                              <div className="min-w-0 flex-1">
                                <span className="font-semibold text-slate-900 block truncate">
                                  {chk.section_heading}
                                </span>
                                <p className="text-[11px] text-slate-500 font-mono line-clamp-1 mt-0.5">
                                  "{chk.snippet}"
                                </p>
                              </div>
                              <div className="flex items-center gap-3 shrink-0 font-mono text-[11px]">
                                <span className="text-slate-600">
                                  #{chk.pre_rank} → #{chk.post_rank}
                                </span>
                                {isPromoted && (
                                  <span className="inline-flex items-center gap-0.5 text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded font-bold">
                                    <ArrowUpRight className="size-3 text-emerald-600" /> +{chk.rank_change}
                                  </span>
                                )}
                                {isDemoted && (
                                  <span className="inline-flex items-center gap-0.5 text-rose-700 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded">
                                    <ArrowDownRight className="size-3 text-rose-600" /> {chk.rank_change}
                                  </span>
                                )}
                                {!isPromoted && !isDemoted && (
                                  <span className="text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                                    Unchanged
                                  </span>
                                )}
                                <span className="text-amber-800 font-bold bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                                  Score: {chk.relevance_score}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Vector Search Diagnostics Table */}
                  {span.name === "vector_search" && (span.attributes?.retrieved_chunks?.length ?? 0) > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-sky-700 uppercase tracking-wider">
                          Vector Retrieval Candidate Chunks ({span.attributes?.retrieved_chunks?.length || 0})
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Top K = {span.attributes?.top_k || 0}
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-1.5">
                        {span.attributes?.retrieved_chunks?.map((chk: any, idx: number) => (
                          <div
                            key={chk.chunk_id || idx}
                            className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs"
                          >
                            <div className="min-w-0 pr-2">
                              <span className="font-semibold text-slate-900 block truncate">
                                #{idx + 1} {chk.section_heading}
                              </span>
                              <p className="text-[11px] text-slate-500 font-mono truncate mt-0.5">
                                "{chk.snippet}"
                              </p>
                            </div>
                            <span className="font-mono text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded shrink-0 font-bold">
                              Cos Sim: {chk.score}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Raw Span Attributes JSON */}
                  <div className="space-y-1 pt-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Span Metadata Attributes
                    </span>
                    <pre className="p-3 rounded-lg bg-slate-900 text-slate-100 text-[11px] font-mono overflow-x-auto">
                      {JSON.stringify(span.attributes, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
