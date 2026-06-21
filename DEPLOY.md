# Deploy

## What changed (since last deploy)

**Backend (Render):**
- `Dockerfile.api` — embedding model is now baked into the image. Cold starts no longer pay the 5-9s HuggingFace download.
- `packages/mvp/src/reporelay_mvp/github.py` — GitHub search timeout cut from 15s → 5s.
- `packages/mvp/src/reporelay_mvp/recommend.py` — disk-backed search cache (24h TTL) + skip GitHub search when DB pool already has ≥200 candidates.

**Frontend (Vercel):**
- `apps/site/src/pages/*` — every page's `cachedFetch` now has an 8s timeout via `AbortController`, a "still searching…" indicator that fires after 3s, and a retry button on every error state. No more silent hangs.

**Keepalive:**
- `.github/workflows/ping.yml` — now also hits `/recommend?repo=fastapi/fastapi&limit=1&tags=python` so the embedding model is loaded into RAM between pings, not just on first real user request.

## Deploy steps

### 1. Render (API)

Render watches your repo and auto-rebuilds on push to the connected branch.

```bash
git add Dockerfile.api packages/mvp/ .github/workflows/
git commit -m "perf: bake model into image + faster search + client timeouts"
git push
```

Then in the Render dashboard:
1. Wait for the build to start (or trigger **Manual Deploy → Clear build cache & deploy** if it doesn't pick up the push).
2. First build will be slower (~30s extra) because it downloads the 130MB model.
3. Watch the logs for `embedding model preloaded and ready` — that's how you know the model is in the image.

**Verify it works:**
```bash
curl -w "\n%{http_code} in %{time_total}s\n" \
  "https://reporelay-mvp-api-0w1k.onrender.com/recommend?repo=fastapi/fastapi&limit=3"
```
Should return 200 in **under 1 second** on a warm container, **under 5 seconds** on a cold one (was 15-25s before).

### 2. Vercel (site)

Vercel also auto-rebuilds on push. No env var changes needed — `PUBLIC_API_URL` is already set to the Render URL.

```bash
# same push as above — Vercel picks it up automatically
```

**Verify in browser:**
1. Open the Vercel URL.
2. Click any repo. The page should render in <100ms and recommendations should appear in <1s.
3. If you see "still searching…" for more than 3 seconds, something is wrong — open DevTools → Network and check the `/recommend` request.

### 3. UptimeRobot (prevent cold starts entirely)

You said you have UptimeRobot set up for the Vercel site. **Add the Render API too** — this is the single biggest win because it stops Render from ever spinning down:

1. UptimeRobot → Add New Monitor
2. Monitor Type: **HTTP(s)**
3. URL: `https://reporelay-mvp-api-0w1k.onrender.com/health`
4. Monitoring Interval: **5 minutes** (Render's free plan spins down at 15min)
5. Save

With UptimeRobot pinging every 5min, the Render container **never goes cold** and the GitHub Actions keepalive becomes belt-and-suspenders.

### 4. Verify the keepalive is doing its job

After deploy, wait 25 minutes (longer than Render's spin-down window) without hitting the site yourself. Then:

```bash
curl -w "\n%{http_code} in %{time_total}s\n" \
  "https://reporelay-mvp-api-0w1k.onrender.com/recommend?repo=fastapi/fastapi&limit=3"
```

If the keepalive + UptimeRobot are working, this should still be **under 1 second**. If it's 5+ seconds, the model got unloaded — check the GitHub Actions tab to make sure the cron is firing.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Render build fails on `sentence_transformers` import | The `RUN python -c ...` step needs the package installed first. Make sure `uv sync` runs before the model download in the Dockerfile. |
| Model still downloads on cold start | `HF_HOME` not set in the running container. Check the deployed env vars in Render. |
| Vercel site shows "failed to load API" | `PUBLIC_API_URL` got unset. Vercel → Settings → Environment Variables. |
| `/recommend` still takes 5+ seconds | Render cold start + model not pre-baked. Check Render build logs for the model download step. |
| GitHub Actions ping failing | Repo → Settings → Actions → Workflow permissions → "Read and write permissions" (needed for some setups). |

## Cost note

Render free plan: 750 hours/month, sleeps after 15min idle. With UptimeRobot pinging every 5min, you stay well within free tier and never sleep. No change needed.
