# TODO

Tracked follow-ups from the architecture review. Two groups: **CORE** addresses the data-flow issues (the recommender is starving for data), **PUBLIC-FACING** is the work needed before opening the site to real users.

---

## CORE — fix the corpus

The current code uses the local DB as the candidate source, with a hand-seeded pool of 4–8 repos. GitHub search is only a fallback and its results are thrown away. Flip the architecture so GitHub is the corpus and the DB is a cache.

- [ ] **Flip the corpus** — rewrite `packages/mvp/src/reporelay_mvp/recommend.py` so GitHub search is the primary candidate source, not the DB fallback
- [ ] **Fix the `search_repos` query** in `packages/mvp/src/reporelay_mvp/github.py:170-181` — OR the source's topics instead of picking one, paginate to 200+ candidates, add `archived:false`, lower the `stars:>100` floor (or make it a parameter)
- [ ] **Persist search hits** — add a `search_fetched_at` timestamp column to `mvp_repos` and upsert results from `search_repos` so the DB grows from real queries instead of manual `save` commands
- [ ] **Drop the hardcoded `0.5` cosine** for ephemeral candidates (`recommend.py:138`) — embed them at query time on the top N, or use the search API's relevance as a proxy
- [ ] **Fix the silent tag-filter fallback** in `packages/mvp/src/reporelay_mvp/candidates.py:80-84` — when the filter eliminates everything, the code currently keeps the unfiltered list with only a log line; either surface this to the caller or remove the fallback
- [ ] **Collapse the duplicate buttons** in `apps/site/src/pages/repo/[owner]/[name].astro:137-145` — "rerun with new seed" and "different results" run identical handlers
- [ ] **Remove the seed-time illusion** — the 8 example repos on `apps/site/src/pages/index.astro:4-13` only exist because the recommender can't function with an empty DB; once the corpus is real, replace with a "trending" list

---

## PUBLIC-FACING — needed before opening the site to real users

Treat GitHub as a **background data source**, not a real-time dependency. The request path should never block on it.

- [ ] **Swap to a GitHub App** — 12,500 req/hr per installation vs 5,000 for a personal token, plus a 30 req/sec burst on REST
- [ ] **Add Redis** as a hot cache in front of Postgres — keys: `rec:{owner}/{name}` (TTL ~12h) and `search:{lang}:{topic}` (TTL ~24h)
- [ ] **Background worker** that pre-computes recommendations for the top ~1,000 repos every 6–12 hours — this absorbs 99% of traffic before it ever hits GitHub
- [ ] **Stale-while-revalidate on cache miss** — return a fallback list (top stars in the source's language) instantly, enqueue a compute job, next request serves the real result
- [ ] **Edge-cache the HTML pages** — set `Cache-Control: public, s-maxage=300, stale-while-revalidate=3600` and put the site behind a CDN (Cloudflare / Vercel / CloudFront)
- [ ] **Per-IP rate limiting at the edge** — protect the origin from a single user spamming the recompute path
- [ ] **Graceful degradation** — if GitHub is down or the worker queue is full, the site still serves *something* (cached results, popular fallback, "try one of these" list)
