"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchPaper, type PaperDetail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BookOpen, FileText } from "lucide-react";

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    fetchPaper(id)
      .then(setPaper)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="h-8 w-3/4 animate-pulse rounded bg-muted" />
        <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-muted" />
        <div className="mt-6 h-24 animate-pulse rounded bg-muted" />
        <div className="mt-8 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <FileText className="size-12 text-muted-foreground" />
        <p className="text-muted-foreground">Could not load paper</p>
        <Button variant="outline" onClick={() => router.push("/papers")}>
          Back to papers
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Title */}
      <h1 className="text-2xl font-semibold leading-tight text-foreground">
        {paper.title}
      </h1>

      {/* Authors */}
      <p className="mt-2 text-sm text-muted-foreground">
        {paper.authors.length > 0
          ? paper.authors.join(", ")
          : "Unknown authors"}
      </p>

      {/* Metadata */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {paper.year && <Badge variant="outline">{paper.year}</Badge>}
        <Badge variant="secondary">{paper.status}</Badge>
        {paper.source_url && (
          <a
            href={paper.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm underline underline-offset-2 text-muted-foreground hover:text-foreground"
          >
            Source
          </a>
        )}
      </div>

      {/* Abstract */}
      {paper.abstract && (
        <section className="mt-8">
          <h2 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Abstract
          </h2>
          <p className="text-sm leading-relaxed text-foreground">
            {paper.abstract}
          </p>
        </section>
      )}

      {/* Sections accordion */}
      {paper.sections.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Sections ({paper.sections.length})
          </h2>
          <div className="space-y-1">
            {paper.sections.map((section) => (
              <details
                key={section.id}
                className="group rounded-lg border border-border"
              >
                <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium transition-colors hover:bg-muted/50">
                  <BookOpen className="size-3.5 shrink-0 text-muted-foreground" />
                  <span>{section.heading}</span>
                </summary>
                {section.content && (
                  <div className="border-t border-border px-4 py-3 text-sm leading-relaxed text-muted-foreground">
                    {section.content}
                  </div>
                )}
              </details>
            ))}
          </div>
        </section>
      )}

      {/* Ask about this paper */}
      <div className="mt-8">
        <Button onClick={() => router.push(`/chat?paper=${paper.id}`)}>
          Ask about this paper
        </Button>
      </div>
    </div>
  );
}
