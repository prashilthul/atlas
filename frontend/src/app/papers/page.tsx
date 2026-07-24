"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchPapers, type Paper } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, FileText, Layers } from "lucide-react";

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
      {/* Search */}
      <div className="relative mb-8">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by title or author..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
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
        <div className="flex flex-col items-center gap-4 py-16">
          <FileText className="size-12 text-muted-foreground" />
          <p className="text-muted-foreground">No papers uploaded yet</p>
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
                <CardContent>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {paper.year && (
                      <Badge variant="outline" className="text-[10px]">
                        {paper.year}
                      </Badge>
                    )}
                    <span className="flex items-center gap-1">
                      <Layers className="size-3" />
                      {paper.section_count} sections
                    </span>
                    <span className="text-muted-foreground">{paper.status}</span>
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
    </div>
  );
}
