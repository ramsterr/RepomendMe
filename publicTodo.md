# RepoRelay — TODO

## For later
- [ ] make a technical blog 

## Gonna start here

- [x] Initialize project repository (monorepo structure)
- [x] Choose and set up tech stack (language, framework, database)
- [x] Configure development environment (linting, formatting, CI)
- [x] Set up environment variables and secrets management (local-dev .env + pydantic-settings; production secrets manager still TODO)
- [ ] Write project conventions doc (branch naming, commit style)
  - [ ] Add branch naming + commit message conventions to keepinmind.md

## Design Decisions

- [x] Add framework choice (Astro over Next.js) to considerations.md
- [ ] Document future stack/framework decisions in considerations.md as they arise

## Data Pipeline

- [x] Set up GitHub API client (auth + rate limiting done; pagination pending)
  - [ ] Add pagination helper for list endpoints (search, repos-by-topic, etc.)
- [ ] Ingest seed data: top N repos per topic/language
- [ ] Ingest repo metadata (topics, stars, forks, language, license)
- [ ] Ingest README files (for embeddings / NLP)
- [ ] Ingest dependency manifests (`package.json`, `Cargo.toml`, `requirements.txt`, etc.)
- [ ] Ingest contributor data (committers, PR authors per repo)
- [ ] Ingest co-starring patterns (users starring multiple repos)
- [ ] Ingest workflow files (CI config, GitHub Actions)
- [ ] Build incremental / periodic refresh pipeline (stay fresh)
- [ ] Store raw data in a relational store (Postgres / SQLite)

## Graph Database

- [x] Choose graph DB (chose Apache AGE — one Postgres with pgvector + AGE)
- [x] Design graph schema (in compass/05-data-model.md)
  - [x] Nodes: `Repo`, `User`, `Topic`, `Language`, `Dependency`
  - [x] Edges: `DEPENDS_ON`, `STARRED_BY`, `CONTRIBUTED_TO`, `HAS_TOPIC`, `CO_OCCURS_IN_WORKFLOW`, `IS_ALTERNATIVE_TO`, etc.
- [ ] Translate schema into SQL DDL (migrations)
- [ ] Ingest data into graph DB from raw store
- [ ] Compute and write edge weights / strengths
- [ ] Index graph for fast traversal queries
- [ ] Verify graph consistency with smoke tests
