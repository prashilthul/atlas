"use client";

import { useEffect, useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// --- Types ---

interface LatencyRow {
  step: string;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  sample_count: number;
}

interface PerPaperRow {
  paper_id: string;
  title: string;
  citation_count: number;
  avg_citation_accuracy: number;
}

interface MetricsSummary {
  health_score: number;
  components: {
    latency: { score: number; weight: number };
    empty_result_rate: { score: number; weight: number };
    citation_accuracy: { score: number; weight: number };
  };
  details: {
    latency_percentiles: LatencyRow[];
    empty_result_rate_24h: number;
    avg_citation_accuracy: number;
  };
  per_paper: PerPaperRow[];
}

interface TimeseriesPoint {
  date: string;
  span_counts: {
    total: number;
    embed: number;
    search: number;
    rerank: number;
    generate: number;
  };
  avg_latency_ms: {
    embed: number;
    search: number;
    rerank: number;
    generate: number;
  };
  token_usage: {
    input: number;
    output: number;
  };
  empty_search_count: number;
}

interface TimeseriesResponse {
  range_days: number;
  data: TimeseriesPoint[];
}

interface LowScoreRow {
  query: string;
  score: number;
  timestamp: string;
}

// --- helpers ---

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function healthColor(score: number): string {
  if (score < 60) return "#dc2626";
  if (score < 80) return "#d97706";
  return "#16a34a";
}

// --- SVG Gauge ---

function HealthGauge({ score }: { score: number }) {
  const r = 72;
  const cx = 100;
  const cy = 100;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score / 100);
  const color = healthColor(score);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="200" height="200" viewBox="0 0 200 200" className="-rotate-90">
        {/* Background track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#e5e5e5"
          strokeWidth="12"
        />
        {/* Foreground arc */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
        {/* Center text */}
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="central"
          className="rotate-90"
          fontSize="36"
          fontWeight="700"
          fill={color}
        >
          {score}
        </text>
      </svg>
      <span className="text-sm font-medium text-muted-foreground">
        Health Score
      </span>
    </div>
  );
}

// --- Custom tooltip (text only, no emoji) ---

function ChartTooltip({
  active,
  payload,
  label,
  valueFormatter,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  valueFormatter?: (v: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-sm shadow-sm">
      <p className="mb-1 font-medium text-foreground">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-muted-foreground">
          <span
            className="inline-block mr-1.5 size-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          {entry.name}: {valueFormatter ? valueFormatter(entry.value) : entry.value}
        </p>
      ))}
    </div>
  );
}

// --- Loading skeleton ---

function SkeletonCard() {
  return (
    <Card>
      <CardHeader>
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="h-48 animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}

// --- EmptyState ---

function EmptyState({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}

// --- Error banner ---

function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <span>{message}</span>
      <button
        onClick={onRetry}
        className="ml-4 rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
      >
        Retry
      </button>
    </div>
  );
}

// --- Faithfulness Trend ---

function computeQualityScore(point: TimeseriesPoint): number {
  const searchCount = point.span_counts.search;
  if (searchCount === 0) return 1;
  return Math.round((1 - point.empty_search_count / searchCount) * 1000) / 1000;
}

function FaithfulnessTrend({
  data7d,
  data30d,
  loading,
}: {
  data7d: TimeseriesPoint[];
  data30d: TimeseriesPoint[];
  loading: boolean;
}) {
  const chartData = useMemo(() => {
    const days = new Map<string, { date: string; score7d: number | null; score30d: number | null }>();

    for (const p of data7d) {
      const key = p.date.slice(0, 10);
      if (!days.has(key)) days.set(key, { date: key, score7d: null, score30d: null });
      days.get(key)!.score7d = computeQualityScore(p);
    }

    for (const p of data30d) {
      const key = p.date.slice(0, 10);
      if (!days.has(key)) days.set(key, { date: key, score7d: null, score30d: null });
      days.get(key)!.score30d = computeQualityScore(p);
    }

    return Array.from(days.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [data7d, data30d]);

  if (loading) return <SkeletonCard />;
  if (chartData.length === 0)
    return <EmptyState message="No data yet" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search quality</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#bfbfbf" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: "#595959" }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 11, fill: "#595959" }}
            />
            <Tooltip
              content={<ChartTooltip valueFormatter={(v) => (v * 100).toFixed(1) + "%"} />}
            />
            <Legend
              formatter={(value) => (
                <span className="text-xs text-muted-foreground">{value}</span>
              )}
            />
            <Line
              type="monotone"
              dataKey="score7d"
              name="7-day"
              stroke="#404040"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="score30d"
              name="30-day"
              stroke="#8c8c8c"
              strokeWidth={2}
              dot={false}
              connectNulls
              strokeDasharray="4 3"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Per-paper citation accuracy ---

function PerPaperAccuracy({
  data,
  loading,
}: {
  data: PerPaperRow[];
  loading: boolean;
}) {
  const chartData = useMemo(
    () =>
      data
        .map((d) => ({
          title: d.title
            ? d.title.length > 35
              ? d.title.slice(0, 35) + "..."
              : d.title
            : `Paper ${d.paper_id.slice(0, 8)}`,
          accuracy: d.avg_citation_accuracy,
        }))
        .sort((a, b) => a.accuracy - b.accuracy),
    [data]
  );

  if (loading) return <SkeletonCard />;
  if (chartData.length === 0) return <EmptyState message="No data yet" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Citation accuracy per paper</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 48)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid stroke="#bfbfbf" strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 1]}
              tick={{ fontSize: 11, fill: "#595959" }}
            />
            <YAxis
              dataKey="title"
              type="category"
              tick={{ fontSize: 11, fill: "#404040" }}
              width={160}
            />
            <Tooltip
              content={<ChartTooltip valueFormatter={(v) => (v * 100).toFixed(1) + "%"} />}
            />
            <Bar
              dataKey="accuracy"
              fill="#595959"
              radius={[0, 3, 3, 0]}
              maxBarSize={16}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Latency breakdown ---

function LatencyBreakdown({
  data,
  loading,
}: {
  data: LatencyRow[];
  loading: boolean;
}) {
  const chartData = useMemo(() => {
    const order = ["embed", "vector_search", "rerank", "generate"];
    const items = data.filter((d) => order.includes(d.step));
    const sorted = items.sort(
      (a, b) => order.indexOf(a.step) - order.indexOf(b.step)
    );
    return sorted.map((d) => ({
      step: d.step === "vector_search" ? "search" : d.step,
      p50: d.p50_ms,
      p95: d.p95_ms,
    }));
  }, [data]);

  if (loading) return <SkeletonCard />;
  if (chartData.length === 0) return <EmptyState message="No data yet" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latency by step</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} barGap={0} barCategoryGap="20%">
            <CartesianGrid stroke="#bfbfbf" strokeDasharray="3 3" />
            <XAxis
              dataKey="step"
              tick={{ fontSize: 11, fill: "#595959" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#595959" }}
              tickFormatter={(v) => (v >= 1000 ? (v / 1000).toFixed(1) + "s" : Math.round(v) + "ms")}
            />
            <Tooltip
              content={<ChartTooltip valueFormatter={(v) => (v >= 1000 ? (v / 1000).toFixed(2) + "s" : Math.round(v) + "ms")} />}
            />
            <Legend
              formatter={(value) => (
                <span className="text-xs text-muted-foreground">{value}</span>
              )}
            />
            <Bar dataKey="p50" name="p50" fill="#737373" radius={[3, 3, 0, 0]} maxBarSize={28} />
            <Bar dataKey="p95" name="p95" fill="#404040" radius={[3, 3, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Empty result rate sparkline ---

function EmptyResultRate({
  data,
  loading,
}: {
  data: TimeseriesPoint[];
  loading: boolean;
}) {
  const chartData = useMemo(() => {
    return data.map((p) => {
      const searchCount = p.span_counts.search;
      const rate = searchCount > 0 ? p.empty_search_count / searchCount : 0;
      return {
        date: p.date,
        rate: Math.round(rate * 10000) / 10000,
      };
    });
  }, [data]);

  if (loading) return <SkeletonCard />;
  if (chartData.length === 0) return <EmptyState message="No data yet" />;

  const latestRate = chartData.length > 0 ? chartData[chartData.length - 1].rate : 0;
  const threshold = 0.05;
  const isAboveThreshold = latestRate >= threshold;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Empty result rate</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">24h</span>
            <span
              className={`text-sm font-semibold ${
                isAboveThreshold ? "text-red-600" : "text-green-600"
              }`}
            >
              {(latestRate * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={chartData}>
            <Area
              type="monotone"
              dataKey="rate"
              stroke={isAboveThreshold ? "#dc2626" : "#16a34a"}
              fill={isAboveThreshold ? "#fecaca" : "#bbf7d0"}
              strokeWidth={2}
              dot={false}
            />
            <Tooltip
              content={
                <ChartTooltip
                  valueFormatter={(v) => (v * 100).toFixed(1) + "%"}
                />
              }
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Low-scoring queries table ---

function LowScoringQueries({
  data,
  loading,
}: {
  data: LowScoreRow[];
  loading: boolean;
}) {
  if (loading)
    return (
      <Card>
        <CardHeader>
          <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
        </CardHeader>
        <CardContent>
          <div className="h-32 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );

  if (data.length === 0) return <EmptyState message="No data yet" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent low-scoring queries</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">Score</th>
                <th className="pb-2 pr-4 font-medium">Query</th>
                <th className="pb-2 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-border last:border-0"
                >
                  <td className="py-2.5 pr-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        row.score < 0.6
                          ? "bg-red-50 text-red-700"
                          : row.score < 0.8
                            ? "bg-amber-50 text-amber-700"
                            : "bg-green-50 text-green-700"
                      }`}
                    >
                      {(row.score * 100).toFixed(0)}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-muted-foreground max-w-[250px] truncate">
                    {row.query.length > 50
                      ? row.query.slice(0, 50) + "..."
                      : row.query}
                  </td>
                  <td className="py-2.5 whitespace-nowrap text-muted-foreground">
                    {formatTime(row.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Health Radar (component scores) ---

function HealthRadar({
  summary,
  loading,
}: {
  summary: MetricsSummary | null;
  loading: boolean;
}) {
  if (loading) return <SkeletonCard />;
  if (!summary) return <EmptyState message="No data yet" />;

  const { latency, empty_result_rate, citation_accuracy } = summary.components;
  const data = [
    { metric: "Latency", score: latency.score },
    { metric: "Retrieval", score: empty_result_rate.score },
    { metric: "Citations", score: citation_accuracy.score },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Health breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="72%">
            <PolarGrid stroke="#d9d9d9" />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fontSize: 11, fill: "#404040" }}
            />
            <PolarRadiusAxis
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: "#8c8c8c" }}
            />
            <Radar
              dataKey="score"
              stroke="#1a1a1a"
              fill="#404040"
              fillOpacity={0.35}
              strokeWidth={2}
            />
            <Tooltip
              content={
                <ChartTooltip valueFormatter={(v) => Math.round(v) + "/100"} />
              }
            />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Pipeline activity stacked area ---

function PipelineActivity({
  data,
  loading,
}: {
  data: TimeseriesPoint[];
  loading: boolean;
}) {
  const chartData = useMemo(
    () =>
      data.map((p) => ({
        date: p.date.slice(0, 10),
        Embeddings: p.span_counts.embed,
        Search: p.span_counts.search,
        Rerank: p.span_counts.rerank,
        Generate: p.span_counts.generate,
      })),
    [data]
  );

  if (loading) return <SkeletonCard />;
  if (chartData.length === 0) return <EmptyState message="No data yet" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData}>
            <CartesianGrid stroke="#d9d9d9" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#595959" }} />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 10, fill: "#595959" }}
            />
            <Tooltip />
            <Legend
              formatter={(value) => (
                <span className="text-xs text-muted-foreground">{value}</span>
              )}
            />
            <Area
              type="monotone"
              dataKey="Embeddings"
              stackId="1"
              stroke="#737373"
              fill="#d9d9d9"
            />
            <Area
              type="monotone"
              dataKey="Search"
              stackId="1"
              stroke="#404040"
              fill="#a3a3a3"
            />
            <Area
              type="monotone"
              dataKey="Rerank"
              stackId="1"
              stroke="#262626"
              fill="#737373"
            />
            <Area
              type="monotone"
              dataKey="Generate"
              stackId="1"
              stroke="#171717"
              fill="#404040"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// --- Main page ---

export default function DashboardPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [timeseries7d, setTimeseries7d] = useState<TimeseriesResponse | null>(
    null
  );
  const [timeseries30d, setTimeseries30d] =
    useState<TimeseriesResponse | null>(null);
  const [lowScoreData, setLowScoreData] = useState<LowScoreRow[]>([]);
  const [rerankerStats, setRerankerStats] = useState<any>(null);
  const [tokenUsage, setTokenUsage] = useState<any>(null);
  const [surfacedTraces, setSurfacedTraces] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryRes, ts7dRes, ts30dRes, rerankRes, tokenRes, surfacedRes] = await Promise.all([
        fetch(`${API_BASE}/api/metrics/summary`),
        fetch(`${API_BASE}/api/metrics/timeseries?range=7d`),
        fetch(`${API_BASE}/api/metrics/timeseries?range=30d`),
        fetch(`${API_BASE}/api/metrics/reranker-stats?range=7d`),
        fetch(`${API_BASE}/api/metrics/token-usage?range=7d`),
        fetch(`${API_BASE}/api/metrics/surfaced-traces?limit=5`),
      ]);

      if (!summaryRes.ok) throw new Error("Failed to fetch metrics summary");
      if (!ts7dRes.ok) throw new Error("Failed to fetch 7-day timeseries");
      if (!ts30dRes.ok) throw new Error("Failed to fetch 30-day timeseries");

      const summaryData: MetricsSummary = await summaryRes.json();
      const ts7dData: TimeseriesResponse = await ts7dRes.json();
      const ts30dData: TimeseriesResponse = await ts30dRes.json();

      setSummary(summaryData);
      setTimeseries7d(ts7dData);
      setTimeseries30d(ts30dData);

      if (rerankRes.ok) setRerankerStats(await rerankRes.json());
      if (tokenRes.ok) setTokenUsage(await tokenRes.json());
      if (surfacedRes.ok) setSurfacedTraces(await surfacedRes.json());

      // Try fetching low-scoring queries
      try {
        const lsqRes = await fetch(
          `${API_BASE}/api/metrics/low-scoring-queries`
        );
        if (lsqRes.ok) {
          const lsqData: LowScoreRow[] = await lsqRes.json();
          setLowScoreData(lsqData);
        }
      } catch {
        // endpoint not available yet
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const summaryLoading = loading && !summary;
  const ts7dLoading = loading && !timeseries7d;
  const ts30dLoading = loading && !timeseries30d;
  const hasAnyData =
    summary || timeseries7d || timeseries30d || lowScoreData.length > 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground font-serif tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          System health and RAG pipeline metrics
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} onRetry={fetchData} />
        </div>
      )}

      {/* Empty state -- no data at all */}
      {!loading && !error && !hasAnyData && (
        <EmptyState message="No data yet" />
      )}

      {/* Grid sections */}
      <div className="space-y-6">
        {/* Row 1: Health gauge + Empty rate sparkline */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Health score gauge */}
          <Card>
            <CardContent className="flex items-center justify-center py-6">
              {summaryLoading ? (
                <div className="size-[200px] animate-pulse rounded-full bg-muted" />
              ) : summary ? (
                <HealthGauge score={summary.health_score} />
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <span className="text-sm text-muted-foreground">Health Score</span>
                  <span className="text-4xl font-bold text-muted-foreground">--</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Component scores (latency, empty rate, citation accuracy) */}
          <Card>
            <CardHeader>
              <CardTitle>Component scores</CardTitle>
            </CardHeader>
            <CardContent>
              {summaryLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-4 w-full animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : summary ? (
                <div className="space-y-4">
                  {[
                    {
                      label: "Latency",
                      score: summary.components.latency.score,
                    },
                    {
                      label: "Empty result rate",
                      score: summary.components.empty_result_rate.score,
                    },
                    {
                      label: "Citation accuracy",
                      score: summary.components.citation_accuracy.score,
                    },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {item.label}
                      </span>
                      <span
                        className={`text-sm font-semibold ${
                          item.score < 60
                            ? "text-red-600"
                            : item.score < 80
                              ? "text-amber-600"
                              : "text-green-600"
                        }`}
                      >
                        {item.score}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No data yet</p>
              )}
            </CardContent>
          </Card>

          {/* Empty result rate sparkline */}
          <EmptyResultRate
            data={timeseries7d?.data || []}
            loading={ts7dLoading}
          />
        </div>

        {/* Row 2: Faithfulness trend */}
        <FaithfulnessTrend
          data7d={timeseries7d?.data || []}
          data30d={timeseries30d?.data || []}
          loading={ts7dLoading && ts30dLoading}
        />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <HealthRadar summary={summary} loading={summaryLoading} />
          <PipelineActivity data={timeseries7d?.data || []} loading={ts7dLoading} />
        </div>

        {/* Row 3: Per-paper accuracy + Latency breakdown */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <PerPaperAccuracy
            data={summary?.per_paper || []}
            loading={summaryLoading}
          />
          <LatencyBreakdown
            data={summary?.details.latency_percentiles || []}
            loading={summaryLoading}
          />
        </div>

        {/* Row 4: Reranker Fallback Rate & Token Burn */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Reranker Value & Fallback Rate */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Reranker Fallback Rate</CardTitle>
              {rerankerStats && (
                <Badge variant={rerankerStats.fallback_rate_pct > 15 ? "destructive" : "secondary"}>
                  Fallback: {rerankerStats.fallback_rate_pct}%
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {rerankerStats?.daily?.length > 0 ? (
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={rerankerStats.daily}>
                    <CartesianGrid stroke="#bfbfbf" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="total_calls" name="Total Reranks" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="fallback_calls" name="Fallbacks" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">No reranker stats recorded yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Token Usage & Cost Trend */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Token Cost & Usage Trend</CardTitle>
              {tokenUsage && (
                <Badge variant="outline" className="font-mono text-xs">
                  {tokenUsage.total_tokens?.toLocaleString() || 0} Total Tokens
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {tokenUsage?.daily?.length > 0 ? (
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={tokenUsage.daily}>
                    <CartesianGrid stroke="#bfbfbf" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="input_tokens" name="Input Tokens" stroke="#6366f1" fill="#c7d2fe" />
                    <Area type="monotone" dataKey="output_tokens" name="Output Tokens" stroke="#10b981" fill="#a7f3d0" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">No token usage metrics available.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Row 5: Surfaced Issues & Slow Traces Panel */}
        {surfacedTraces && (surfacedTraces.recent_errors?.length > 0 || surfacedTraces.slow_traces?.length > 0) && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Surfaced Pipeline Issues & Slow Traces</CardTitle>
              <a href="/traces" className="text-xs font-semibold text-blue-600 hover:underline">
                Open Trace Inspector →
              </a>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {/* Recent Errors */}
                <div className="space-y-2">
                  <span className="font-bold text-red-600 tracking-wide uppercase text-[10px]">
                    Recent Errors & Fallbacks ({surfacedTraces.recent_errors?.length || 0})
                  </span>
                  <div className="space-y-1.5">
                    {surfacedTraces.recent_errors?.map((tr: any) => (
                      <div key={tr.trace_id} className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                        <span className="font-mono font-semibold truncate max-w-[180px]">Trace {tr.trace_id.slice(0, 8)}...</span>
                        <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700 bg-amber-50">
                          {tr.has_error ? "Error" : "Rerank Fallback"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Slow Traces */}
                <div className="space-y-2">
                  <span className="font-bold text-amber-600 tracking-wide uppercase text-[10px]">
                    Slow Traces (p95+ &gt; 2s) ({surfacedTraces.slow_traces?.length || 0})
                  </span>
                  <div className="space-y-1.5">
                    {surfacedTraces.slow_traces?.map((tr: any) => (
                      <div key={tr.trace_id} className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                        <span className="font-mono font-semibold truncate max-w-[180px]">Trace {tr.trace_id.slice(0, 8)}...</span>
                        <span className="font-mono font-bold text-slate-700">{tr.total_duration_ms}ms</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Row 6: Low-scoring queries */}
        <LowScoringQueries
          data={lowScoreData}
          loading={loading && lowScoreData.length === 0}
        />
      </div>
    </div>
  );
}
