const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  source_url: string | null;
  status: string;
  chunk_count: number;
  section_count: number;
  created_at: string;
}

export interface Section {
  id: string;
  heading: string;
  level: number;
  content: string | null;
  order_index: number;
}

export interface PaperDetail extends Paper {
  sections: Section[];
}

export interface PapersResponse {
  items: Paper[];
  total: number;
  page: number;
}

export async function fetchPapers(params?: {
  search?: string;
  page?: number;
}): Promise<PapersResponse> {
  const url = new URL(`${API_BASE}/api/papers`);
  if (params?.search) url.searchParams.set("search", params.search);
  if (params?.page) url.searchParams.set("page", String(params.page));

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Failed to fetch papers: ${res.statusText}`);
  return res.json();
}

export async function fetchPaper(id: string): Promise<PaperDetail> {
  const res = await fetch(`${API_BASE}/api/papers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch paper: ${res.statusText}`);
  return res.json();
}
