const API = "http://localhost:8001";

export interface Repo {
  id: number;
  full_name: string;
  description: string | null;
  language: string | null;
  topics: string[];
  stars: number;
}

export interface RecommendResponse {
  source_repo: string;
  repos: Repo[];
}

export async function fetchRecommendations(
  repo: string,
  limit = 10,
  seed?: number,
): Promise<RecommendResponse> {
  const params = new URLSearchParams({ repo, limit: String(limit) });
  if (seed !== undefined) params.set("seed", String(seed));
  const res = await fetch(`${API}/recommend?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "request failed");
  }
  return res.json();
}

export async function fetchExplore(
  seed: number,
  limit = 10,
): Promise<RecommendResponse> {
  const params = new URLSearchParams({
    seed: String(seed),
    limit: String(limit),
  });
  const res = await fetch(`${API}/explore?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "request failed");
  }
  return res.json();
}
