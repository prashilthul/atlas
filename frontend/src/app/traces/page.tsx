"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, RefreshCw, Layers, Filter, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { TraceWaterfall, TraceSpan } from "@/components/trace-waterfall";

interface TraceListItem {
  trace_id: string;
  created_at: string;
  total_duration_ms: number;
  span_count: number;
  has_error: boolean;
  has_fallback: boolean;
  query: string;
}

interface TraceDetailData {
  trace_id: string;
  created_at: string;
  total_duration_ms: number;
  spans: TraceSpan[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getBaseUrl(): string {
  if (API_BASE) return API_BASE;
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export default function TraceInspectorPage() {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [traceDetail, setTraceDetail] = useState<TraceDetailData | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadTraces = useCallback(async () => {
    setLoading(true);
    try {
      const base = getBaseUrl();
      const url = new URL(`${base}/api/traces`);
      if (search) url.searchParams.set("search", search);
      if (statusFilter !== "all") url.searchParams.set("status", statusFilter);
      url.searchParams.set("limit", "50");

      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setTraces(data.items || []);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    loadTraces();
  }, [loadTraces]);

  const loadTraceDetail = async (traceId: string) => {
    setSelectedTraceId(traceId);
    setLoadingDetail(true);
    try {
      const base = getBaseUrl();
      const res = await fetch(`${base}/api/traces/${traceId}`);
      if (res.ok) {
        const data = await res.json();
        setTraceDetail(data);
      }
    } catch {
      setTraceDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900 p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-xs">
              <Layers className="size-4" />
            </div>
            <h1 className="font-serif text-2xl font-semibold tracking-tight text-slate-900">
              Pipeline Trace Inspector
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time Gantt charts, retrieval diagnostics, and span latency profiling across RAG execution runs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadTraces}
            className="h-8 border-slate-300 text-slate-700 hover:bg-slate-100"
          >
            <RefreshCw className="size-3.5 mr-1.5" /> Refresh Traces
          </Button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Trace ID or user query..."
            className="h-8 pl-9 bg-slate-50 border-slate-200 text-xs text-slate-900 focus:bg-white focus:ring-1 focus:ring-slate-400"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <Filter className="size-3.5 text-slate-400 mr-1" />
          {["all", "error", "fallback", "slow"].map((st) => (
            <Button
              key={st}
              variant={statusFilter === st ? "default" : "ghost"}
              size="sm"
              onClick={() => setStatusFilter(st)}
              className={`h-7 text-xs capitalize transition-all ${
                statusFilter === st
                  ? "bg-slate-900 text-white hover:bg-slate-800"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {st === "fallback" ? "Reranker Fallbacks" : st === "slow" ? "Slow (>2.5s)" : st}
            </Button>
          ))}
        </div>
      </div>

      {/* Main Grid View: Table & Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Trace List Table */}
        <div className={`space-y-3 ${selectedTraceId ? "lg:col-span-5" : "lg:col-span-12"}`}>
          <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
            <span>Showing {traces.length} Pipeline Traces</span>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
            {traces.map((tr) => {
              const isSelected = selectedTraceId === tr.trace_id;
              return (
                <div
                  key={tr.trace_id}
                  onClick={() => loadTraceDetail(tr.trace_id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-white border-slate-900 ring-2 ring-slate-900/10 shadow-sm"
                      : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-2xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className="font-semibold text-xs text-slate-900 line-clamp-1">
                      {tr.query}
                    </span>
                    <span className="font-mono text-[11px] text-slate-900 font-bold shrink-0">
                      {tr.total_duration_ms}ms
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                    <span className="font-mono text-slate-400">ID: {tr.trace_id.substring(0, 8)}...</span>
                    <div className="flex items-center gap-1.5">
                      {tr.has_fallback && (
                        <Badge variant="outline" className="text-[10px] border-amber-200 text-amber-700 bg-amber-50">
                          Fallback
                        </Badge>
                      )}
                      {tr.has_error && (
                        <Badge variant="outline" className="text-[10px] border-rose-200 text-rose-700 bg-rose-50">
                          Error
                        </Badge>
                      )}
                      {!tr.has_error && !tr.has_fallback && (
                        <Badge variant="outline" className="text-[10px] border-emerald-200 text-emerald-700 bg-emerald-50">
                          OK
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {traces.length === 0 && !loading && (
              <div className="p-8 text-center bg-white border border-slate-200 rounded-xl text-slate-400 text-xs">
                No pipeline traces found matching current filter.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Selected Trace Gantt Chart & Diagnostic View */}
        {selectedTraceId && (
          <div className="lg:col-span-7 space-y-4">
            {loadingDetail ? (
              <div className="p-8 bg-white border border-slate-200 rounded-xl text-center text-xs text-slate-500">
                Loading trace execution timeline...
              </div>
            ) : traceDetail ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                  <div>
                    <h2 className="text-xs font-bold text-slate-900 font-mono">
                      Trace ID: {traceDetail.trace_id}
                    </h2>
                    <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                      Executed: {new Date(traceDetail.created_at).toLocaleString()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedTraceId(null)}
                    className="text-xs text-slate-400 hover:text-slate-900 h-7"
                  >
                    <X className="size-3.5 mr-1" /> Close
                  </Button>
                </div>

                {/* Real Gantt / Waterfall Chart */}
                <TraceWaterfall spans={traceDetail.spans} totalDurationMs={traceDetail.total_duration_ms} />
              </div>
            ) : (
              <div className="p-8 bg-white border border-slate-200 rounded-xl text-center text-xs text-slate-500">
                Trace details unavailable.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
