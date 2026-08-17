"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Trash2,
  MessageSquare,
  Search,
  Calendar,
  ExternalLink,
  Sparkles,
  Layers,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { fetchPaper, deletePaper, type PaperDetail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { showToast } from "@/components/toast";
import { ConfirmModal } from "@/components/confirm-modal";

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const handleDelete = async () => {
    if (!paper) return;
    try {
      await deletePaper(paper.id);
      showToast("success", "Paper Deleted", `"${paper.title}" was removed successfully.`);
      router.push("/papers");
    } catch {
      showToast("error", "Delete Failed", "Failed to delete paper. Please try again.");
    }
  };

  useEffect(() => {
    setLoading(true);
    setError(false);
    fetchPaper(id)
      .then((data) => {
        setPaper(data);
        // Expand first 3 sections by default if available
        if (data.sections?.length > 0) {
          const initial = new Set(data.sections.slice(0, 2).map((s) => s.id));
          setExpandedSections(initial);
        }
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  const toggleSection = (secId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(secId)) next.delete(secId);
      else next.add(secId);
      return next;
    });
  };

  const expandAll = () => {
    if (!paper) return;
    setExpandedSections(new Set(paper.sections.map((s) => s.id)));
  };

  const collapseAll = () => {
    setExpandedSections(new Set());
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10 space-y-6">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-lg bg-slate-200 animate-pulse" />
          <div className="h-4 w-24 bg-slate-200 animate-pulse rounded" />
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-8 space-y-4">
          <div className="h-9 w-3/4 animate-pulse rounded-lg bg-slate-200" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
          <div className="flex gap-2 pt-2">
            <div className="h-6 w-16 animate-pulse rounded-full bg-slate-200" />
            <div className="h-6 w-20 animate-pulse rounded-full bg-slate-200" />
          </div>
        </div>
        <div className="h-32 animate-pulse rounded-2xl bg-slate-200" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-200" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center">
        <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-rose-50 border border-rose-200 text-rose-600 mb-4 shadow-sm">
          <FileText className="size-7" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Paper Not Found</h2>
        <p className="mt-1 text-sm text-slate-500">
          The requested research paper could not be loaded or has been deleted.
        </p>
        <Button variant="outline" className="mt-6 rounded-xl border-slate-300" onClick={() => router.push("/papers")}>
          <ArrowLeft className="size-4 mr-2" /> Back to Paper Library
        </Button>
      </div>
    );
  }

  const filteredSections = paper.sections.filter(
    (sec) =>
      sec.heading.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (sec.content && sec.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "ready":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 font-medium px-2.5 py-0.5 inline-flex items-center gap-1">
            <CheckCircle2 className="size-3" /> Ready
          </Badge>
        );
      case "processing":
        return (
          <Badge className="bg-amber-50 text-amber-700 border-amber-200 font-medium px-2.5 py-0.5 inline-flex items-center gap-1 animate-pulse">
            <Clock className="size-3" /> Processing
          </Badge>
        );
      default:
        return (
          <Badge className="bg-rose-50 text-rose-700 border-rose-200 font-medium px-2.5 py-0.5 inline-flex items-center gap-1">
            <AlertTriangle className="size-3" /> {status}
          </Badge>
        );
    }
  };

  return (
    <main className="min-h-[calc(100vh-3.5rem)] bg-slate-50/50 pb-20">
      {/* Top Bar / Navigation */}
      <div className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-14 z-20">
        <div className="mx-auto max-w-5xl px-6 py-3.5 flex items-center justify-between gap-4">
          <Link
            href="/papers"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="size-4" />
            Back to Papers
          </Link>

          <div className="flex items-center gap-2">
            <Button
              onClick={() => router.push(`/chat?paper=${paper.id}`)}
              className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl shadow-md transition-all hover:shadow-lg gap-2"
            >
              <MessageSquare className="size-3.5" />
              Ask Paper Pilot
            </Button>

            <Button
              variant="outline"
              size="sm"
              className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:border-rose-300 rounded-xl text-xs"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="size-3.5 mr-1" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-6 pt-8 space-y-8">
        {/* Paper Header / Hero Card */}
        <section className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
            <BookOpen className="size-48 text-slate-900" />
          </div>

          <div className="relative z-10 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              {getStatusBadge(paper.status)}
              {paper.year && (
                <Badge variant="outline" className="border-slate-300 text-slate-700 gap-1 font-mono text-xs">
                  <Calendar className="size-3" />
                  {paper.year}
                </Badge>
              )}
              {paper.source_url && (
                <a
                  href={paper.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 hover:underline underline-offset-4 ml-auto"
                >
                  Original Source <ExternalLink className="size-3" />
                </a>
              )}
            </div>

            <h1 className="font-serif text-2xl sm:text-3xl font-semibold leading-tight text-slate-900">
              {paper.title}
            </h1>

            <p className="text-sm font-medium text-slate-600">
              {paper.authors.length > 0 ? (
                <span className="flex flex-wrap items-center gap-1">
                  <span className="text-slate-400">Authors:</span> {paper.authors.join(", ")}
                </span>
              ) : (
                <span className="italic text-slate-400">Authors not specified</span>
              )}
            </p>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100">
              <div className="rounded-xl bg-slate-50 p-3 border border-slate-100">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Sections</div>
                <div className="text-lg font-bold text-slate-900 mt-0.5">{paper.section_count}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 border border-slate-100">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Embedded Chunks</div>
                <div className="text-lg font-bold text-slate-900 mt-0.5">{paper.chunk_count}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 border border-slate-100">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Status</div>
                <div className="text-sm font-semibold capitalize text-slate-800 mt-1">{paper.status}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 border border-slate-100">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Added</div>
                <div className="text-sm font-semibold text-slate-800 mt-1">
                  {new Date(paper.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Abstract Section */}
        {paper.abstract && (
          <section className="rounded-3xl border border-slate-200 bg-gradient-to-b from-white to-slate-50/50 p-6 sm:p-8 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="size-4 text-amber-500" />
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-700">
                Abstract Summary
              </h2>
            </div>
            <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line font-normal">
              {paper.abstract}
            </p>
          </section>
        )}

        {/* Paper Sections Accordion / Explorer */}
        {paper.sections.length > 0 && (
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Layers className="size-4 text-slate-700" />
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-900">
                  Paper Structure & Content ({paper.sections.length})
                </h2>
              </div>

              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={expandAll} className="text-xs text-slate-600 hover:text-slate-900">
                  Expand All
                </Button>
                <span className="text-slate-300">|</span>
                <Button variant="ghost" size="sm" onClick={collapseAll} className="text-xs text-slate-600 hover:text-slate-900">
                  Collapse All
                </Button>
              </div>
            </div>

            {/* Section Search Filter */}
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search within section headings or text..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 rounded-xl bg-white border-slate-200 text-sm shadow-xs focus:border-slate-400"
              />
            </div>

            {/* Sections List */}
            <div className="space-y-3 pt-1">
              {filteredSections.length === 0 ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                  No sections found matching "{searchQuery}"
                </div>
              ) : (
                filteredSections.map((section) => {
                  const isExpanded = expandedSections.has(section.id);
                  const wordCount = section.content ? section.content.split(/\s+/).length : 0;
                  return (
                    <div
                      key={section.id}
                      className={`rounded-2xl border transition-all bg-white shadow-xs ${
                        isExpanded ? "border-slate-300 ring-1 ring-slate-200" : "border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <button
                        onClick={() => toggleSection(section.id)}
                        className="w-full flex items-center justify-between p-4 text-left gap-3 focus:outline-none"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span
                            className={`flex size-6 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold ${
                              section.level === 1
                                ? "bg-slate-900 text-white"
                                : "bg-slate-100 text-slate-700 border border-slate-200"
                            }`}
                          >
                            H{section.level}
                          </span>
                          <span className="text-sm font-semibold text-slate-900 truncate">
                            {section.heading}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          {wordCount > 0 && (
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
                              {wordCount} words
                            </span>
                          )}
                          <span className="text-xs text-slate-400 hover:text-slate-600 font-medium">
                            {isExpanded ? "Collapse" : "Expand"}
                          </span>
                        </div>
                      </button>

                      {isExpanded && section.content && (
                        <div className="border-t border-slate-100 p-4 sm:p-5 bg-slate-50/50 rounded-b-2xl space-y-3">
                          <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line font-normal">
                            {section.content}
                          </p>
                          <div className="pt-2 flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/chat?paper=${paper.id}&q=Explain section "${section.heading}"`);
                              }}
                              className="text-xs rounded-lg border-slate-300 text-slate-700 hover:bg-white gap-1.5 shadow-xs"
                            >
                              <MessageSquare className="size-3 text-slate-500" />
                              Ask about this section
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </section>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Delete Research Paper?"
        description={`Are you sure you want to permanently delete "${paper.title}"? All extracted sections and vector embeddings will be removed.`}
        confirmText="Delete Paper"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </main>
  );
}
