const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getBaseUrl(): string {
  if (API_BASE) return API_BASE;
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

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
  page_size: number;
}

export async function fetchPapers(params?: {
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PapersResponse> {
  const base = getBaseUrl();
  const url = new URL(`${base}/api/papers`);
  if (params?.search) url.searchParams.set("search", params.search);
  if (params?.page) url.searchParams.set("page", String(params.page));
  if (params?.page_size) url.searchParams.set("page_size", String(params.page_size));

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Failed to fetch papers: ${res.statusText}`);
  return res.json();
}

export async function fetchPaper(id: string): Promise<PaperDetail> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/api/papers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch paper: ${res.statusText}`);
  return res.json();
}

export async function deletePaper(id: string): Promise<void> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/api/papers/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete paper: ${res.statusText}`);
}
