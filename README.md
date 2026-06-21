# RepoRelay

A GitHub repo recommender. Give it a repo, get back repos you might also care about. No ML training, no user data, no graph walking — just Postgres + pgvector + a pre-trained embedding model + six weighted features.

[→ Architecture doc (how each stage works, the database schema, what the embedding model does)](ARCHITECTURE.md)

## How it works

Six steps, each one a file:

| Step | File | What it does |
|---|---|---|
| 1. Data | `data.py` | Reads/writes a single `mvp_repos` table in Postgres |
| 2. Candidates | `candidates.py` | Gathers a pool via SQL filter (same language/topics) + pgvector ANN |
| 3. Features | `features.py` | Computes 7 signals per (source, candidate) pair |
| 4. Score | `score.py` | Weighted sum of the features — two weight schemes (default and tag-filtered) |
| 5. Rerank | `rerank.py` | Drops same-owner repos, enforces one-per-owner diversity |
| 6. Embedding | `embedding.py` | Runs `BAAI/bge-small-en-v1.5` to turn README text into 384-dim vectors |

The recommendation pipeline (`recommend.py`) orchestrates all six stages and also pulls fresh candidates from the GitHub Search API on every request, persisting them back to the database so the corpus grows over time.

### Features

The system computes these signals for each (source, candidate) pair:

| Feature | What it captures |
|---|---|
| `language_match` | Same programming language? |
| `topic_overlap` | Jaccard similarity of GitHub topic sets |
| `cosine_sim` | Semantic similarity of README embeddings (pgvector) |
| `dep_overlap` | Shared package dependencies |
| `popularity_sim` | Log-scale star count similarity |
| `trending_boost` | Velocity signal from github.com/trending |
| `filter_cosine_sim` | Semantic match against user-provided tag filter text (only when tags are provided) |

### Scoring weights

Default weights (no tag filter):
```python
WEIGHTS = {
    "language_match": 0.25,
    "topic_overlap": 0.25,
    "cosine_sim": 0.20,
    "dep_overlap": 0.15,
    "popularity_sim": 0.05,
    "trending_boost": 0.10,
}
```

Tag-filtered weights (when the user provides tags like "react, typescript"):
```python
TAG_WEIGHTS = {
    "language_match": 0.10,
    "topic_overlap": 0.20,
    "cosine_sim": 0.10,
    "filter_cosine_sim": 0.30,  # semantic match against the tag text
    "dep_overlap": 0.10,
    "popularity_sim": 0.10,
    "trending_boost": 0.10,
}
```

When a `seed` is provided, weights are jittered by +/-10% deterministically and `popularity_sim` is boosted 3x to surface "cooler" repos.

---

## Getting started

You need **Docker** (or Homebrew for Mac), **Python 3.12+**, **uv**, and **Node.js** (for the site).

### 1. Get a GitHub token

Go to https://github.com/settings/tokens, create a classic token (no scopes needed), and set up your `.env`:

```bash
echo 'DATABASE_URL=postgresql+psycopg://reporelay:reporelay@localhost:5439/reporelay' > .env
echo 'GITHUB_TOKEN=ghp_your_token_here' >> .env
```

### 2. Start Postgres

**Docker (recommended):**
```bash
just up
```

**Homebrew (Mac):**
```bash
brew install pgvector
pg_ctl -D /opt/homebrew/var/postgresql@16 start
createdb reporelay
echo 'DATABASE_URL=postgresql+psycopg://YOUR_USER@localhost:5432/reporelay' >> .env
```

### 3. Install dependencies

```bash
just sync
```

This installs Python packages (FastAPI, SQLAlchemy, sentence-transformers, httpx, etc.) and the Astro site's Node dependencies.

### 4. Create the database table

```bash
just migrate
```

Runs Alembic migrations to create the `mvp_repos` table. You only do this once.

### 5. Put some repos in the database

```bash
just mvp save fastapi/fastapi
just mvp save django/django
just mvp save pallets/flask
just mvp save psf/requests
```

Each `save` command:
1. Calls the GitHub API for the repo's metadata (language, topics, stars, dependencies)
2. Fetches the README and runs it through `BAAI/bge-small-en-v1.5` to get a 384-dim embedding
3. Stores everything in `mvp_repos`

The embedding model downloads the first time (~11 seconds), then stays in memory.

### 6. Ask for recommendations

```bash
just mvp recommend fastapi/fastapi --limit 5
```

This looks up the repo in the database, pulls fresh candidates from GitHub Search, computes features, scores them, and prints a ranked list.

```
recommendations for fastapi/fastapi

   1. pallets/flask  (Python, 71680 stars, topics: python, flask, wsgi)
   2. psf/requests   (Python, 54043 stars, topics: python, http, forhumans)
   3. django/django  (Python, 87917 stars, topics: python, django, web)
```

### 7. Seed the corpus (optional but recommended)

For better recommendations, bulk-index repos by language:

```bash
just mvp seed --languages python,typescript --per-language 50
```

This searches GitHub for top repos in each language and stores them. The more repos in the database, the better the candidate pool.

### 8. Scrape trending repos (optional)

```bash
just mvp trending --since daily
```

Scrapes github.com/trending for repos with viral growth. These get a `trending_score` that feeds into the `trending_boost` feature.

---

## Running the API server

```bash
just api                                         # starts on port 8001
curl "localhost:8001/recommend?repo=django/django&limit=5"
```

### Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `GET /recommend?repo=owner/name&limit=10&seed=42&tags=react,typescript` | Ranked recommendations |
| `GET /explore?seed=42&limit=10` | Surprise me — random repo + its recs |
| `GET /popular?limit=8&topic=python` | Top repos by stars (homepage) |
| `GET /topics?limit=40` | Top topics by DB frequency (explore page) |
| `POST /webhooks/github` | GitHub webhook receiver for push events |

### Tag filtering

Pass `?tags=react,typescript` to `/recommend`. The system embeds the tag text and compares it semantically against every candidate's README embedding — so "machine learning" will match repos about ML even if they don't have that exact tag.

### Seed-based variation

Pass `?seed=42` to get different but deterministic results. Same seed = same results. Useful for "rerun with a different mix."

---

## Running the web UI

```bash
just dev                                         # starts API (8001) + Astro site (4321)
```

Open http://localhost:4321. The site has three pages:

- `/` — search box + "try one of these" popular repos
- `/repo/owner/name` — card-style recommendations with tag filtering and "rerun with new seed"
- `/explore` — topic browser + "surprise me" random repo

The frontend is vanilla Astro with no framework. Client-side caching via sessionStorage avoids redundant API calls when navigating between pages.

---

## GitHub webhooks

RepoRelay can subscribe to `push` events on watched repos. When a repo's README changes on its default branch, the webhook clears its embedding so the next embed pass re-computes it.

```bash
# Set a webhook secret in .env
echo 'GITHUB_WEBHOOK_SECRET=any_random_string' >> .env

# The webhook endpoint is at POST /webhooks/github
```

---

## CLI commands

```bash
just mvp save owner/name               fetch + persist + embed a repo
just mvp count                          show how many repos are stored
just mvp recommend owner/name           print ranked recommendations
just mvp explore                        surprise me — random repo, recs
just mvp seed                           bulk-index repos from GitHub Search
just mvp embed                          embed READMEs of un-embedded repos
just mvp trending                       scrape github.com/trending
```

---

## Project structure

```
packages/mvp/                              # the recommender engine
  src/reporelay_mvp/
    recommend.py       orchestrates the full pipeline
    embedding.py       BAAI/bge-small-en-v1.5 wrapper (async, numpy)
    candidates.py      pool generation (SQL filter + pgvector ANN)
    features.py        computes 7 signals per pair
    score.py           weighted sum (default + tag-filtered weights)
    rerank.py          dedup + diversity
    data.py            queries + upserts
    github.py          fetch repos from GitHub API
    trending.py        scrape github.com/trending
    seed.py            bulk corpus indexing
    embed_pass.py      bulk README embedding
    cli.py             typer CLI
    db.py              SQLAlchemy session management
    models.py          Pydantic models
    settings.py        env-based config
    migrations/        Alembic migrations

apps/mvp_api/                              # FastAPI server
  src/reporelay_mvp_api/
    main.py            /health, /recommend, /explore, /popular, /topics
    webhooks.py        GitHub webhook receiver

apps/site/                                 # Astro frontend
  src/
    pages/
      index.astro          homepage (search + popular repos)
      explore.astro        topic browser + surprise me
      repo/[owner]/[name]  recommendation results
    layouts/Base.astro     shared HTML shell
    lib/api.ts             typed API helpers (unused by pages)
    styles/global.css      design system
```

---

## What this doesn't do

- No user tracking or personalization
- No collaborative filtering (needs real star/fork events from users)
- No graph-based traversal
- No Redis caching (GitHub search results are cached in-memory with a 5-minute TTL)
- No feedback loop

---

## Tech stack

| Layer | Technology |
|---|---|
| Embedding model | `BAAI/bge-small-en-v1.5` (384 dims, via sentence-transformers) |
| Database | PostgreSQL 16 + pgvector (HNSW index for ANN search) |
| API | FastAPI (async, uvicorn) |
| Frontend | Astro 5 (SSR, vanilla JS, no framework) |
| Deployment | Vercel (site) + Render (API) |
| Package manager | uv (Python) + pnpm (Node) |
| Task runner | just |

---

## License

MIT
