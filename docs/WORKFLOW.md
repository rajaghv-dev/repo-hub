# Workflow — Machine Lifecycle

repo-hub is designed around one principle: **the machine is disposable, the data is not**. You clone, run, push, clean. Repeat anywhere.

---

## Setup on Any New Machine

```bash
# 1. Clone
git clone https://github.com/rajaghv-dev/repo-hub
cd repo-hub

# 2. Environment — only secrets, no data
cp .env.example .env
# Edit .env with 4 values:
#   GITHUB_TOKEN     → https://github.com/settings/tokens  (repo:read scope)
#   HF_TOKEN         → https://huggingface.co/settings/tokens  (read scope)
#   DATABASE_URL     → your PostgreSQL connection string (Supabase / Neon)
#   REPO_HUB_GCS_BUCKET → your GCS bucket name

# 3. Install
pip install -e .          # installs into whatever Python env is active

# 4. Verify connections
repo-hub doctor           # checks GitHub token, HF token, PG connection, GCS access

# 5. Restore working state from cloud
repo-hub restore          # pulls GCS cache → data/, verifies PG has data

# 6. Browse immediately (queries PG — no local data needed)
repo-hub list --top 20
repo-hub search "MLIR-based inference engine"
```

---

## Full Pipeline Run

```bash
# Run everything, push all results, wipe local data
repo-hub all --clean

# What this does, in order:
#  1. restore      pull existing GCS cache to data/ (skip already-cached files)
#  2. fetch        GitHub API → data/cache/  (skip if cache fresh)
#  3. hf-fetch     HuggingFace Hub → data/hf/
#  4. scrape       dep files for repos >50★ → data/deps/
#  5. classify     ontology keyword match → PostgreSQL
#  6. embed        bge-small embeddings → pgvector in PG
#  7. score        composite score → PG
#  8. digest       compute what changed since last run → PG
#  9. export       Parquet + summary.json → GCS
# 10. report       generate REPORT.md
# 11. push         GCS sync + git commit + git push REPORT.md
# 12. clean        rm -rf data/   ← machine is clean
```

Run time estimate (with GitHub token, 75 orgs):
- Fetch: ~15 min (rate-limited, cached on repeat)
- Dep scrape: ~20 min (async, 5 workers)
- Classify + embed + score: ~3 min (10k repos, CPU)
- Export + push: ~2 min
- **Total: ~40 min first run, ~10 min with warm cache**

---

## Incremental / Daily Use

```bash
# Quick update — only fetch what changed, re-score, push
repo-hub all --incremental --clean

# Just browse (no fetch, reads PG directly)
repo-hub list --domain ai_compiler --min-score 60
repo-hub list --status bookmarked
repo-hub search "FPGA HLS inference"
repo-hub show intel/openvino --explain

# Annotate a repo (writes to PG immediately)
repo-hub annotate microsoft/onnxruntime \
    --status in-use \
    --tags "inference,onnx,ep" \
    --note "Check EP plugin API for custom hardware backends" \
    --project suryaos-laptop

# See what changed since last run
repo-hub digest
repo-hub digest --since 7d       # last 7 days
repo-hub digest --domain fpga    # only FPGA domain changes
```

---

## After a Full Run — What's in the Cloud

### PostgreSQL
- All repos classified with scores, domain assignments, matched signals
- pgvector embeddings for semantic search
- Dependency graph edges
- Your annotations and notes
- Digest log of changes

### GCS
```
gs://your-bucket/repo-hub/
├── cache/orgs/          ← raw GitHub API responses
├── cache/deps/          ← scraped dep files
├── hf/                  ← HuggingFace model cards
├── exports/YYYY-MM-DD/  ← repos.parquet, repos.csv, summary.json
└── snapshots/           ← point-in-time PG table dumps
```

### GitHub
- `REPORT.md` auto-committed (top repos per domain, domain stats, new finds)
- Any changes you made to `config/profile.yaml` or `config/orgs.yaml`

### Local
- Nothing. Clean.

---

## DuckDB on Parquet (analytics without PG)

The Parquet export in GCS is queryable directly with DuckDB — no PostgreSQL needed:

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET gcs_credential_chain='workload_identity';")

# Query directly from GCS
con.execute("""
    SELECT org, COUNT(*) as repos, AVG(score) as avg_score
    FROM 'gs://your-bucket/repo-hub/exports/2025-04-28/repos.parquet'
    WHERE score > 0.5
    GROUP BY org
    ORDER BY avg_score DESC
""").df()
```

Useful for ad-hoc analysis or when you don't have the `.env` with `DATABASE_URL` handy.

---

## Shared Access (multiple machines / team)

Since all state is in cloud:
- Multiple machines can run `repo-hub list` / `annotate` simultaneously against the same PG
- Annotations from one machine are immediately visible on another (PG is the single source)
- Concurrent `repo-hub all` runs should be avoided — use `--dry-run` on secondary machines if PG already has fresh data
- The GCS cache is safe for concurrent reads; writes use object-level replace (idempotent)

---

## First-time PostgreSQL Setup

Run `schema.sql` once against your PostgreSQL instance:

```bash
# Supabase (via their SQL editor, or psql)
psql $DATABASE_URL -f schema.sql

# Or with repo-hub
repo-hub db init          # runs schema.sql, verifies extensions are available
```

Required PostgreSQL extensions (pre-installed on Supabase/Neon):
- `vector` (pgvector)
- `pg_trgm` (trigram fuzzy search)
- `uuid-ossp`

---

## Scheduled Runs

For automatic weekly refresh, run `repo-hub all --clean` in any CI/CD or cron environment:

```yaml
# GitHub Actions: .github/workflows/refresh.yml
name: Weekly repo-hub refresh
on:
  schedule:
    - cron: '0 2 * * 0'   # every Sunday 02:00 UTC
  workflow_dispatch:        # manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - run: repo-hub all --clean
        env:
          GITHUB_TOKEN:          ${{ secrets.GITHUB_TOKEN }}
          HF_TOKEN:              ${{ secrets.HF_TOKEN }}
          DATABASE_URL:          ${{ secrets.DATABASE_URL }}
          REPO_HUB_GCS_BUCKET:   ${{ secrets.REPO_HUB_GCS_BUCKET }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: weekly repo-hub refresh"
          file_pattern: REPORT.md
```

This means **you never have to run it manually** — it updates itself every Sunday and pushes `REPORT.md` to GitHub automatically.

---

## Commands Reference

| Command | Needs local data? | Needs PG? | Needs GCS? |
|---|---|---|---|
| `list` | No | Yes | No |
| `show` | No | Yes | No |
| `search` | No | Yes (pgvector) | No |
| `annotate` | No | Yes | No |
| `digest` | No | Yes | No |
| `stats` | No | Yes | No |
| `fetch` | Yes (writes) | No | Yes (writes) |
| `classify` | Yes (reads) | Yes (writes) | No |
| `embed` | No | Yes (writes) | No |
| `score` | No | Yes (writes) | No |
| `export` | No | Yes (reads) | Yes (writes) |
| `restore` | Yes (writes) | No | Yes (reads) |
| `push` | Yes (reads) | No | Yes (writes) |
| `clean` | Yes (deletes) | No | No |
| `all` | Yes (temp) | Yes | Yes |
| `db init` | No | Yes | No |
| `doctor` | No | Yes | Yes |
