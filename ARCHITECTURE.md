# Architecture

There's no training, no ML pipeline, no model that learns. The system has three pieces that already know how to do their job:

- **GitHub API** — tells you what a repo *is* (language, topics, stars, README)
- **all-MiniLM-L6-v2** — a pre-trained sentence transformer that turns any text into 384 numbers (an embedding). It already knows that "Python web framework" and "async Python API" are similar concepts.
- **Postgres + pgvector** — stores the data and finds repos with nearby embeddings

You never train anything. You fetch data, embed text, run queries. That's it.

---

## System diagram

```
                    ┌──────────────┐
                    │  GitHub API  │
                    └──────┬───────┘
                           │  fetch repo metadata + README
                           ▼
┌──────────────────────────────────────────────────────┐
│                  Ingestion (just mvp save)            │
│                                                      │
│  github.py        httpx → GitHub API                 │
│  embedding.py     sentence-transformers → 384 floats │
│  data.py          INSERT INTO mvp_repos              │
└─────────────────────┬────────────────────────────────┘
                      │
                      ▼
             ┌────────────────┐
             │   Postgres     │
             │  mvp_repos     │
             │  + pgvector    │
             └───────┬────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────┐   ┌───────────┐   ┌──────────┐
│ SQL     │   │ pgvector  │   │ raw row  │
│ filter  │   │ ANN       │   │ lookup   │
│ (lang,  │   │ (cosine   │   │ (by name)│
│ topics) │   │ distance) │   │          │
└────┬────┘   └─────┬─────┘   └────┬─────┘
     │              │              │
     └──────┬───────┘              │
            ▼                      │
     ┌──────────────┐              │
     │  candidates  │◄─────────────┘
     │  (150-250)   │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   features   │  language match, topic overlap,
     │   (5 floats) │  cosine sim, dep overlap, stars sim
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │    score     │  weighted sum → single number
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   rerank     │  drop same-owner, one-per-owner
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  top-N list  │  ← returned to user
     └──────────────┘
```

---

## The mvp_repos table

One table. No joins to other tables, no foreign keys, no materialized views.

```
mvp_repos
├── id            BIGINT        GitHub repo ID
├── owner         VARCHAR       e.g. "fastapi"
├── name          VARCHAR       e.g. "fastapi"
├── full_name     VARCHAR       "fastapi/fastapi"
├── description   TEXT          from GitHub
├── language      VARCHAR       "Python", "TypeScript", etc.
├── topics        TEXT[]        ["python", "json", "swagger-ui"]
├── stars         INTEGER       stargazer count
├── dependencies  TEXT[]        package names from dependency graph
├── embedding     VECTOR(384)   384 floats from sentence-transformers
├── created_at    TIMESTAMPTZ
├── updated_at    TIMESTAMPTZ
└── embedded_at   TIMESTAMPTZ   when embedding was computed

Indexes:
  ix_mvp_repos_language           btree on language
  ix_mvp_repos_topics             GIN on topics (for && overlap queries)
  ix_mvp_repos_stars              btree on stars DESC
  ix_mvp_repos_full_name          btree on full_name (unique)
  ix_mvp_repos_embedding_hnsw     HNSW on embedding (for ANN search)
```

---

## The 5 stages in detail

### Stage 1 — Data

`data.py` reads from and writes to `mvp_repos`. Four queries matter:

| Function | SQL | Purpose |
|---|---|---|
| `get_repo` | `SELECT ... WHERE full_name = ?` | Look up the source repo |
| `fetch_filtered_pool` | `SELECT ... WHERE language = ? OR topics && ?` | "Give me repos in the same ecosystem" |
| `fetch_vector_neighbors` | `CROSS JOIN ... ORDER BY embedding <=> src.embedding` | "Give me repos with similar READMEs" |
| `upsert_repo` | `INSERT ... ON CONFLICT DO UPDATE` | Save a repo (used during ingestion) |

---

### Stage 2 — Features

`features.py` computes 5 numbers for each (source, candidate) pair. All values are in [0, 1].

```
language_match:
  1.0 if source.language == candidate.language
  0.0 otherwise

topic_overlap:
  Jaccard(set(source.topics), set(candidate.topics))
  = |intersection| / |union|
  Captures: "do these repos live in the same category?"

cosine_sim:
  1 - (source.embedding <=> candidate.embedding)
  The pgvector <=> operator computes cosine distance
  Captures: "do the READMEs talk about similar things?"

dep_overlap:
  Jaccard(set(source.dependencies), set(candidate.dependencies))
  Captures: "do they use the same libraries?"

popularity_sim:
  1 - |log1p(source.stars) - log1p(candidate.stars)| / log1p(500000)
  Captures: "are they at a similar scale?"
  (Log scale because 100 vs 200 stars matters more than 50k vs 51k)
```

---

### Stage 3 — Candidate Generation

`candidates.py` runs two queries and merges:

1. **SQL filter** — `WHERE language = ? OR topics && ?` — uses the btree and GIN indexes. Fast, returns repos in the same ecosystem regardless of README similarity. Max 250.

2. **pgvector ANN** — `ORDER BY embedding <=> source.embedding` — uses the HNSW index. Returns the most semantically similar repos by README content. Max 150.

The two pools are deduplicated by repo ID. Vector pool repos take priority (they carry accurate cosine similarity). SQL-only repos get a neutral cosine sim of 0.5.

Result: ~150-250 candidates, down from potentially thousands.

---

### Stage 4 — Scoring

`score.py` multiplies each feature by a weight and sums:

```
score = 0.30 × language_match
      + 0.30 × topic_overlap
      + 0.20 × cosine_sim
      + 0.15 × dep_overlap
      + 0.05 × popularity_sim
```

The weights are hand-picked and live in a dict at the top of the file. No ML, no training. Change the numbers and the ranking changes immediately.

```python
WEIGHTS = {
    "language_match": 0.30,
    "topic_overlap": 0.30,
    "cosine_sim": 0.20,
    "dep_overlap": 0.15,
    "popularity_sim": 0.05,
}
```

Why these weights? Language and topic overlap are the strongest signals for "is this repo even in the same ballpark." Cosine similarity refines within that. Dependencies are a good tiebreaker. Popularity is a weak signal but prevents recommending micro-repos alongside massive ones.

---

### Stage 5 — Reranking

`rerank.py` applies three rules after scoring:

1. **Drop same-owner** — if source is `fastapi/fastapi`, don't recommend `fastapi/fastapi` (defensive) or `fastapi/typer` (same org, probably not useful)

2. **One per owner** — at most one repo per GitHub org/user in the final list. Prevents "here are 10 Facebook repos"

3. **Cap at limit** — return the top N that survive the filters

---

## The embedding model

The model is `sentence-transformers/all-MiniLM-L6-v2` from HuggingFace. It was trained on 1B+ sentence pairs across many domains to predict which sentences are paraphrases of each other. It converts text into 384 numbers where semantically similar texts get nearby vectors.

The model is loaded once on first use (takes ~11 seconds on a Mac), then cached in memory for subsequent calls.

The README text fed to the model is truncated to the first 8000 characters. For most repos, the first 8000 chars of README capture the project's purpose, installation, and basic usage — enough for semantic similarity.

**You never train, fine-tune, or update this model.** It's a fixed building block, like `import json`.

---

## What's NOT in this system

| Not present | Why it was skipped |
|---|---|
| Training / ML pipeline | Weights are hand-tuned, model is pre-trained |
| User data / profiles | No personalization needed for content-based recs |
| Collaborative filtering | Needs real star/fork events from users |
| Redis / caching | Queries are fast enough at <10k repos |
| Graph traversal (2-hop) | SQL filter + pgvector covers the same ground simpler |
| Feedback loop | Not needed to demonstrate the core loop |
| Multiple strategies / blending | One strategy with 5 features is enough |
| Co-star / workflow signals | These need data the MVP doesn't collect |

---

## The data you need to put in

The system only recommends repos you've ingested. If you have 3 repos in `mvp_repos`, it can only recommend among those 3 (minus the source). To get good recommendations:

1. **Ingest repos in related domains** — if you want Python web framework recs, ingest a bunch of Python web repos
2. **Aim for 20-50 repos** — that gives the candidate pool enough variety
3. **Ingest repos with READMEs** — repos without READMEs get a zero embedding and only match on structured features

```bash
# Example: build a Python web ecosystem
just mvp save fastapi/fastapi
just mvp save django/django
just mvp save pallets/flask
just mvp save encode/starlette
just mvp save psf/requests
just mvp save urllib3/urllib3
just mvp save aio-libs/aiohttp
just mvp save tiangolo/sqlmodel
just mvp save sqlalchemy/sqlalchemy
```
