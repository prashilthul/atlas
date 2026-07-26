"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Send, ChevronDown, ChevronRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---

interface CitationData {
  chunk_id: string;
  paper_id: string;
  section_heading: string;
  marker: string;
}

interface TraceSpanData {
  name: string;
  duration_ms: number;
  status: "ok" | "error" | "skipped";
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationData[];
  trace_id?: string;
  trace_spans?: TraceSpanData[];
  streaming?: boolean;
}

// --- SSE event parser ---

async function* streamSSE(
  response: Response
): AsyncGenerator<{ event: string; data: unknown }> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const lines = part.split("\n");
      let event = "";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) dataStr = line.slice(6);
      }
      if (event && dataStr) {
        try {
          yield { event, data: JSON.parse(dataStr) };
        } catch {
          yield { event, data: dataStr };
        }
      }
    }
  }
}

// --- Trace waterfall component ---

const TRACE_STEPS = ["embed", "vector_search", "rerank", "generate", "judge"];

function stepLabel(name: string): string {
  const labels: Record<string, string> = {
    embed: "Embed",
    vector_search: "Search",
    rerank: "Rerank",
    generate: "Generate",
    judge: "Judge",
  };
  return labels[name] || name;
}

function statusBadge(status: string): string {
  if (status === "ok") return "OK";
  if (status === "error") return "Error";
  if (status === "skipped") return "Skipped";
  return status;
}

function statusColor(status: string): string {
  if (status === "ok") return "text-green-700";
  if (status === "error") return "text-red-600";
  return "text-gray-400";
}

function TraceTimeline({
  spans,
  trace_id,
}: {
  spans?: TraceSpanData[];
  trace_id?: string;
}) {
  const steps: TraceSpanData[] = spans?.length
    ? spans
    : TRACE_STEPS.map((name) => ({
        name,
        duration_ms: 0,
        status: "skipped" as const,
      }));

  return (
    <div className="relative pl-5">
      {/* Vertical line */}
      <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />

      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={step.name} className="relative flex items-center gap-3">
            {/* Dot */}
            <div
              className={`absolute -left-[17px] size-3 rounded-full border-2 ${
                step.status === "ok"
                  ? "border-green-500 bg-green-50"
                  : step.status === "error"
                    ? "border-red-400 bg-red-50"
                    : "border-gray-300 bg-gray-50"
              }`}
            />
            {/* Name */}
            <span className="text-sm text-foreground min-w-[100px]">
              {stepLabel(step.name)}
            </span>
            {/* Duration */}
            <span className="text-xs text-muted-foreground font-mono min-w-[60px]">
              {step.duration_ms > 0
                ? step.duration_ms >= 1000
                  ? `${(step.duration_ms / 1000).toFixed(1)}s`
                  : `${step.duration_ms}ms`
                : "--"}
            </span>
            {/* Status badge */}
            <span
              className={`text-xs font-medium ${statusColor(step.status)}`}
            >
              {statusBadge(step.status)}
            </span>
          </div>
        ))}
      </div>

      {trace_id && !spans?.length && (
        <p className="mt-2 text-xs text-muted-foreground">
          Trace: {trace_id.slice(0, 8)}...
        </p>
      )}
    </div>
  );
}

// --- Citation popover content ---

function CitationPopover({
  citation,
  children,
}: {
  citation: CitationData;
  children: React.ReactNode;
}) {
  return (
    <Popover>
      <PopoverTrigger className="inline text-xs align-super leading-none font-medium text-muted-foreground hover:text-foreground cursor-pointer underline-offset-2 hover:underline">
        {children}
      </PopoverTrigger>
      <PopoverContent side="top" align="center" className="w-72 p-3">
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-medium text-foreground">Section:</span>{" "}
            {citation.section_heading || "Unknown section"}
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-medium text-foreground">Paper:</span>{" "}
            {citation.paper_id.slice(0, 8)}...
          </p>
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Chunk:</span>{" "}
            {citation.chunk_id.slice(0, 8)}...
          </p>
        </div>
      </PopoverContent>
    </Popover>
  );
}

// --- Message content renderer ---

function renderAssistantContent(
  content: string,
  citations?: CitationData[]
) {
  if (!citations?.length) {
    return <p className="whitespace-pre-wrap">{content}</p>;
  }

  const parts: React.ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <span key={`t-${lastIndex}`}>
          {content.slice(lastIndex, match.index)}
        </span>
      );
    }

    const markerNum = parseInt(match[1], 10);
    const citation = citations.find(
      (c) => c.marker === `[${markerNum}]`
    );

    if (citation) {
      parts.push(
        <CitationPopover key={`c-${match.index}`} citation={citation}>
          [{markerNum}]
        </CitationPopover>
      );
    } else {
      parts.push(
        <sup
          key={`c-${match.index}`}
          className="text-xs align-super leading-none text-muted-foreground"
        >
          [{markerNum}]
        </sup>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push(
      <span key={`t-${lastIndex}`}>{content.slice(lastIndex)}</span>
    );
  }

  return <p className="whitespace-pre-wrap">{parts}</p>;
}

// --- Main component ---

export default function ChatPage() {
  const searchParams = useSearchParams();
  const paperId = searchParams.get("paper");
  const paperIds: string[] | undefined = paperId ? [paperId] : undefined;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(
    new Set()
  );
  const [activeCitation, setActiveCitation] =
    useState<CitationData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const toggleTrace = (msgId: string) => {
    setExpandedTraces((prev) => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  };

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || sending) return;

      setSending(true);
      setError(null);

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: query.trim(),
      };

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            paper_ids: paperIds,
            session_id: sessionId,
            stream: true,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errBody = await res.text();
          throw new Error(errBody || `HTTP ${res.status}`);
        }

        let accumulated = "";
        let finalCitations: CitationData[] | undefined;
        let finalTraceId: string | undefined;
        let finalTraceSpans: TraceSpanData[] | undefined;

        for await (const ev of streamSSE(res)) {
          if (ev.event === "token") {
            const d = ev.data as { text?: string };
            if (d.text) {
              accumulated += d.text;
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  copy[copy.length - 1] = { ...last, content: accumulated };
                }
                return copy;
              });
            }
          } else if (ev.event === "done") {
            const d = ev.data as {
              citations?: CitationData[];
              trace_id?: string;
              trace_spans?: TraceSpanData[];
              session_id?: string;
            };
            finalCitations = d.citations;
            finalTraceId = d.trace_id;
            finalTraceSpans = d.trace_spans;
            if (d.session_id) setSessionId(d.session_id);
          } else if (ev.event === "error") {
            const d = ev.data as { message?: string };
            throw new Error(d.message || "Unknown error");
          }
        }

        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant" && last.streaming) {
            copy[copy.length - 1] = {
              ...last,
              content: accumulated,
              citations: finalCitations,
              trace_id: finalTraceId,
              trace_spans: finalTraceSpans,
              streaming: false,
            };
          }
          return copy;
        });

        if (finalTraceId && !sessionId) {
          setSessionId(finalTraceId);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = err instanceof Error ? err.message : "Request failed";
        setError(msg);
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant" && last.streaming) {
            copy[copy.length - 1] = {
              ...last,
              content: last.content || "Sorry, something went wrong.",
              streaming: false,
            };
          }
          return copy;
        });
      } finally {
        setSending(false);
        abortRef.current = null;
        inputRef.current?.focus();
      }
    },
    [sending, paperIds, sessionId]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-full">
      {/* Left panel — chat */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {messages.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <h2 className="text-lg font-medium text-foreground mb-2">
                Paper Pilot Chat
              </h2>
              <p className="text-sm text-muted-foreground max-w-sm">
                Ask questions about your uploaded papers. The assistant will
                cite sources and show its reasoning trace.
              </p>
              {paperId && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Filtering to paper: {paperId.slice(0, 8)}...
                </p>
              )}
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-xl px-4 py-2.5 ${
                  msg.role === "user"
                    ? "bg-charcoal-800 text-white rounded-br-sm"
                    : "bg-cream-50 text-charcoal-900 rounded-bl-sm ring-1 ring-foreground/5"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="whitespace-pre-wrap text-sm">
                    {msg.content}
                  </p>
                ) : (
                  <div className="text-sm leading-relaxed">
                    {msg.streaming && !msg.content ? (
                      <span className="inline-flex items-center gap-1">
                        <span className="size-1.5 rounded-full bg-foreground/40 animate-pulse" />
                        <span className="size-1.5 rounded-full bg-foreground/40 animate-pulse [animation-delay:150ms]" />
                        <span className="size-1.5 rounded-full bg-foreground/40 animate-pulse [animation-delay:300ms]" />
                      </span>
                    ) : (
                      renderAssistantContent(msg.content, msg.citations)
                    )}

                    {msg.streaming && msg.content && (
                      <span className="inline-block w-1.5 h-4 bg-foreground/40 animate-pulse ml-0.5 align-text-bottom" />
                    )}

                    {/* Trace waterfall */}
                    {!msg.streaming && (msg.trace_id || msg.trace_spans) && (
                      <div className="mt-3 pt-2 border-t border-border/50">
                        <button
                          onClick={() => toggleTrace(msg.id)}
                          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {expandedTraces.has(msg.id) ? (
                            <ChevronDown className="size-3" />
                          ) : (
                            <ChevronRight className="size-3" />
                          )}
                          See trace
                        </button>
                        {expandedTraces.has(msg.id) && (
                          <div className="mt-2">
                            <TraceTimeline
                              spans={msg.trace_spans}
                              trace_id={msg.trace_id}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {error && !sending && (
            <div className="flex justify-center">
              <div className="bg-red-50 text-red-700 text-sm rounded-lg px-4 py-2 ring-1 ring-red-200">
                {error}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-border px-4 py-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your papers..."
              disabled={sending}
              className="flex-1"
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || sending}
            >
              <Send className="size-4" />
            </Button>
          </form>
        </div>
      </div>

      {/* Right panel — paper viewer */}
      <div className="hidden lg:block w-96 border-l border-border bg-card">
        <div className="h-full flex flex-col">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-medium text-foreground">
              Paper Viewer
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {activeCitation ? (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Section:
                  </span>{" "}
                  {activeCitation.section_heading || "Unknown"}
                </p>
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Paper ID:
                  </span>{" "}
                  {activeCitation.paper_id}
                </p>
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Chunk ID:
                  </span>{" "}
                  {activeCitation.chunk_id}
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <p className="text-sm text-muted-foreground">
                  Hover over a citation marker to view paper details.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
