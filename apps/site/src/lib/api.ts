export type SlotName =
  | "alternatives"
  | "addons"
  | "companions"
  | "starters"
  | "trending"
  | "maintainer_wanted";

export interface Repo {
  id: number;
  full_name: string;
  description: string | null;
  stars: number;
  language: string | null;
  topics: string[];
}

export interface Slot {
  name: SlotName;
  repos: Repo[];
}

export interface RecommendResponse {
  source_repo: string;
  slots: Slot[];
}

export async function getRecommendations(
  repo: string,
  limit: number,
): Promise<RecommendResponse> {
  const base = import.meta.env.PUBLIC_API_URL ?? "http://localhost:8000";
  const url = new URL("/recommend", base);
  url.searchParams.set("repo", repo);
  url.searchParams.set("limit", String(limit));
  const res = await fetch(url);
  if (!res.ok) {
    return { source_repo: repo, slots: [] };
  }
  return (await res.json()) as RecommendResponse;
}
