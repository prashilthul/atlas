"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchPapers, deletePaper, type Paper } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, FileText, Layers, Trash2, BookOpen } from "lucide-react";
import { showToast } from "@/components/toast";
import { ConfirmModal } from "@/components/confirm-modal";
import { UploadDialog } from "@/components/upload-dialog";

export default function PapersPage() {
  const router = useRouter();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const perPage = 12;

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deletePaper(deleteTarget.id);
      showToast("success", "Paper Deleted", `"${deleteTarget.title || "Paper"}" was removed successfully.`);
      loadPapers();
    } catch {
      showToast("error", "Delete Failed", "Could not remove paper. Please try again.");
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent, id: string, title: string) => {
    e.stopPropagation();
    setDeleteTarget({ id, title: title || "this paper" });
  };

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [search]);

  const loadPapers = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetchPapers({
        search: debouncedSearch || undefined,
        page,
        page_size: perPage,
      });
      setPapers(res.items);
      setTotal(res.total);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, page]);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground">
            Paper Library
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {total > 0
              ? `${total} paper${total === 1 ? "" : "s"} indexed and searchable`
              : "Upload PDFs to start asking grounded questions"}{" "}
            {loading && "• loading..."}
          </p>
        </div>
        <UploadDialog />
      </div>

      <div className="relative mb-8 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title or author..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Error */}
      {error && !loading && (
        <div className="flex flex-col items-center gap-4 py-16">
          <FileText className="size-12 text-muted-foreground" />
          <p className="text-muted-foreground">Could not load papers</p>
          <Button variant="outline" onClick={loadPapers}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && papers.length === 0 && (
        <div className="flex flex-col items-center gap-5 rounded-2xl border border-dashed border-border bg-card py-16 px-6 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-muted">
            <BookOpen className="size-7 text-muted-foreground" />
          </div>
          <div>
            <p className="font-serif text-lg font-semibold text-foreground">
              No papers yet
            </p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
              Upload a research paper in PDF format and it becomes searchable —
              then ask it anything in the chat.
            </p>
          </div>
          <UploadDialog />
        </div>
      )}

      {/* Skeleton */}
      {loading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} size="sm">
              <CardHeader>
                <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                <div className="mt-2 h-3 w-1/2 animate-pulse rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Grid */}
      {!loading && !error && papers.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <Card
                key={paper.id}
                size="sm"
                className="cursor-pointer transition-colors hover:bg-muted/50"
                onClick={() => router.push(`/papers/${paper.id}`)}
              >
                <CardHeader>
                  <CardTitle className="line-clamp-2 text-sm leading-snug">
                    {paper.title}
                  </CardTitle>
                  <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    {paper.authors.length > 0
                      ? paper.authors.slice(0, 2).join(", ")
                      : "Unknown authors"}
                    {paper.authors.length > 2 && (
                      <Badge variant="secondary" className="text-[10px]">
                        +{paper.authors.length - 2} more
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground pt-1">
                    <div className="flex items-center gap-2">
                      {paper.year && (
                        <Badge variant="outline" className="text-[10px] font-medium">
                          {paper.year}
                        </Badge>
                      )}
                      <span className="flex items-center gap-1 font-medium text-slate-600">
                        <Layers className="size-3 text-slate-700" />
                        {paper.section_count} sections
                      </span>
                    </div>
                    <Badge variant={paper.status === "ready" ? "secondary" : "outline"} className="text-[10px] uppercase tracking-wider">
                      {paper.status}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                    <Button
                      size="sm"
                      className="flex-1 h-8 text-xs bg-slate-900 hover:bg-slate-800 text-white font-medium shadow-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/chat?paper=${paper.id}`);
                      }}
                    >
                      Ask Paper Pilot
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs text-slate-700 hover:bg-slate-50"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/papers/${paper.id}`);
                      }}
                    >
                      View
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                      title="Delete paper"
                      onClick={(e) => handleDeleteClick(e, paper.id, paper.title)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete Paper?"
        description={`Are you sure you want to delete "${deleteTarget?.title || "this paper"}"? All associated sections and embeddings will be permanently removed.`}
        confirmText="Delete Paper"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  );
}
