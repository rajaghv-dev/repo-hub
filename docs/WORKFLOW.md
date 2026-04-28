# Workflow — Machine Lifecycle

repo-hub is built on one principle: **the machine is disposable, the data is not**. You clone, run, push, clean. Resume identically on any other machine.

---

## Setup on Any Machine

```bash
# 1. Clone
git clone https://github.com/rajaghv-dev/repo-hub
cd repo-hub

# 2. Secrets only — no data in .env
cp .env.example .env
# Fill in 5 values:
#   GITHUB_TOKEN          → github.com/settings/tokens (repo:read scope)
#   HF_TOKEN              → huggingface.co/settings/tokens (read)
#   DATABASE_URL          → postgresql://user:pass@host:5432/db (Neon/Supabase)
#   GOOGLE_APPLICATION_CREDENTIALS → /path/to/service-account.json
#   REPO_HUB_GCS_BUCKET   → your GCS bucket name

# 3. Install
pip install -e .

# 4. Verify all connections
repo-hub doctor
# Checks: GitHub token + rate limit, HF token, PG connection + extensions,
#         GCS bucket access + write, bge-small model download

# 5. First-time database setup (run once per PG instance)
repo-hub db init          # runs schema.sql, creates extensions, verifies indexes

# 6. Restore working state from cloud
repo-hub restore          # pulls GCS cache delta → data/, verifies PG has data

# 7. Browse immediately — all queries hit PG directly, no local data needed
repo-hub list --top 20
repo-hub search "MLIR-based inference engine"
```

---

## Full Pipeline Run

```bash
# Run everything, push all results, wipe local data
repo-hub all --clean

# Step-by-step what happens:
#  1. restore          pull existing GCS cache to data/ (delta only, skip fresh files)
#  2. pulse            scan RSS/Atom/ArXiv for signals since last run
#  3. fetch            GitHub API → data/cache/  (skip if TTL fresh)
#  4. hf               HuggingFace Hub → data/hf/
#  5. classify         ontology keyword match → PostgreSQL (upsert, idempotent)
#  6. embed            bge-small → pgvector in PG (skip already-embedded repos)
#  7. score            composite score → PG
#  8. digest           compute what changed → PG digest table
#  9. export           Parquet + summary.json → GCS
# 10. report           generate REPORT.md
# 11. push             GCS delta sync + git commit + git push REPORT.md
# 12. clean            rm -rf data/   ← machine is clean (only with --clean flag)

# Run without wiping (keep cache for next time)
repo-hub all

# Quick incremental — only process new/changed repos since last run
repo-hub all --incremental --clean

# Development / testing — sample 10 repos per org max
repo-hub all --sample 10
```

**Run time estimates** (with GitHub token, ~95 orgs):

| Mode | First run | Warm cache |
|---|---|---|
| Full | ~60 min | ~15 min |
| Incremental | ~10 min | ~5 min |
| Sample (10/org) | ~8 min | ~3 min |

---

## Day-to-Day Use

```bash
# Browse by domain (queries PG — no local data needed)
repo-hub list --domain eda_sim --min-score 60
repo-hub list --domain fpga --domain interconnect --active --top 30
repo-hub list --domain soc_riscv --sort stars
repo-hub list --status bookmarked
repo-hub list --org llvm --org iree-org

# Semantic search (pgvector)
repo-hub search "MLIR compiler targeting AMD GPU"
repo-hub search "user-space PCIe DMA Alveo FPGA"
repo-hub search "open RISC-V SoC with Linux support"

# RAG synthesis (Phase 4)
repo-hub ask "What are my options for PCIe DMA from user space to an Alveo card?"
repo-hub ask "Which MLIR dialects target AMD GPU backends?"
repo-hub ask "What changed in the ROCm ecosystem this month?"
repo-hub ask "Which repos span both EDA simulation and AI compilers?"

# Recommendations based on your bookmarks (Phase 4)
repo-hub discover

# Knowledge graph (Phase 3)
repo-hub graph llvm/circt          # deps, contributors, connected repos
repo-hub graph --domain eda_sim    # domain sub-graph

# Detailed repo view
repo-hub show ucb-bar/chipyard --explain
repo-hub show enjoy-digital/litepcie

# Annotate (writes to PG immediately, visible on all machines)
repo-hub annotate spdk/spdk \
    --status in-use \
    --tags "pcie,dma,nvme,userspace" \
    --note "Used in Alveo PCIe DMA path. Check XDMA integration." \
    --project alveo-UCards

repo-hub annotate llvm/circt \
    --status bookmarked \
    --tags "mlir,fpga,eda" \
    --note "FIRRTL lowering passes — follow for HLS→MLIR pipeline"

# Weekly digest
repo-hub digest
repo-hub digest --since 7d
repo-hub digest --since 7d --domain soc_riscv
repo-hub digest --since 7d --domain eda_sim --domain fpga

# Stats
repo-hub stats
repo-hub stats --domain ai_compiler
repo-hub stats --org chipsalliance

# Lightweight hourly signal scan (Phase 2)
repo-hub pulse                     # checks RSS feeds + ArXiv, no token needed
```

---

## After a Full Run — What's in the Cloud

### PostgreSQL
- All repos classified with scores, domain assignments, matched signals
- pgvector embeddings for semantic search (`repo-hub search`, `repo-hub ask`)
- Dependency graph edges (cross-repo relationships)
- Contributor graph (phase 2)
- Signal queue (pulse events, phase 2)
- Star history per repo (trend detection)
- Your annotations and notes
- Digest log of changes

### GCS
```
gs://your-bucket/repo-hub/
├── cache/
│   ├── orgs/          {org}.json  — raw GitHub API (24h TTL)
│   └── deps/          {org}/{repo}/{file}  — scraped dep files
├── hf/
│   ├── models/        {org}/{model}/README.md
│   └── datasets/      {org}/{dataset}/README.md
├── exports/
│   └── {YYYY-MM-DD}/
│       ├── repos.parquet       # columnar, queryable via DuckDB
│       ├── repos.csv
│       └── summary.json
└── snapshots/
    └── {YYYY-MM-DD}.csv        # point-in-time PG table dump
```

### GitHub
- `REPORT.md` auto-committed (top repos per domain, new repos, ecosystem highlights)
- Config changes (`config/profile.yaml`, `config/orgs.yaml`) if you edited them

### Local
- Nothing. Clean.

---

## DuckDB on GCS Parquet (analytics without PG)

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")

# Query Parquet directly from GCS — no PG needed
con.execute("""
    SELECT org, COUNT(*) AS repos, ROUND(AVG(score), 1) AS avg_score,
           ARRAY_AGG(name ORDER BY score DESC)[1:3] AS top_repos
    FROM 'gs://your-bucket/repo-hub/exports/2025-04-28/repos.parquet'
    WHERE score > 50
    GROUP BY org ORDER BY avg_score DESC LIMIT 20
""").df()
```

Useful for ad-hoc analysis or when you don't have the `.env` with `DATABASE_URL` handy.

---

## PostgreSQL Setup (first time on a new PG instance)

```bash
# Option A: Neon (recommended — no auto-pause on free tier)
# Create project at neon.tech, copy connection string to DATABASE_URL

# Option B: Supabase
# Create project at supabase.com, use the "URI" connection string
# Note: free tier pauses after 7 days of inactivity

# Option C: local Docker
docker run -d -e POSTGRES_PASSWORD=pw -p 5432:5432 ankane/pgvector

# Run schema
repo-hub db init
# Or manually:
psql $DATABASE_URL -f schema.sql
```

**Required PostgreSQL extensions** (pre-installed on Neon and Supabase):
- `vector` (pgvector)
- `pg_trgm`
- `uuid-ossp`

---

## Scheduled Runs — GitHub Actions

```yaml
# .github/workflows/refresh.yml
name: Weekly repo-hub refresh
on:
  schedule:
    - cron: '0 2 * * 0'     # every Sunday 02:00 UTC
  workflow_dispatch:          # manual trigger anytime

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - name: Cache HuggingFace model
        uses: actions/cache@v4
        with:
          path: ~/.cache/huggingface
          key: hf-bge-small-v1

      - run: pip install -e .

      - run: repo-hub all --clean
        env:
          GITHUB_TOKEN:                    ${{ secrets.GITHUB_TOKEN }}
          HF_TOKEN:                        ${{ secrets.HF_TOKEN }}
          DATABASE_URL:                    ${{ secrets.DATABASE_URL }}
          GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCS_SA_JSON_PATH }}
          REPO_HUB_GCS_BUCKET:             ${{ secrets.REPO_HUB_GCS_BUCKET }}

      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: weekly repo-hub refresh [skip ci]"
          file_pattern: REPORT.md
```

This means **you never have to run it manually** — it self-updates every Sunday.

**GitHub Actions GCS authentication:** Store the service account JSON as a GitHub secret (`GCS_SA_JSON`). In the workflow, write it to a temp file and set `GOOGLE_APPLICATION_CREDENTIALS` to that path:

```yaml
      - name: Write GCS credentials
        run: |
          echo '${{ secrets.GCS_SA_JSON }}' > /tmp/gcs-sa.json
          echo "GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs-sa.json" >> $GITHUB_ENV
```

---

## Command Reference

| Command | Needs `data/`? | Needs PG? | Needs GCS? | Notes |
|---|---|---|---|---|
| `doctor` | No | Yes | Yes | Run first on any new machine |
| `db init` | No | Yes | No | Run once per PG instance |
| `restore` | Writes | No | Yes | Delta pull — fast on warm cache |
| `fetch` | Writes | No | Writes | GitHub API pagination |
| `hf` | Writes | No | Writes | HuggingFace Hub API |
| `pulse` | No | Writes | No | Lightweight, no token needed |
| `classify` | Reads | Writes | No | Idempotent upsert |
| `embed` | No | Writes | No | Reads PG, writes pgvector |
| `score` | No | Writes | No | Reads + updates PG |
| `digest` | No | Writes | No | Reads PG, computes delta |
| `export` | No | Reads | Writes | Parquet + CSV + JSON |
| `report` | No | Reads | No | Generates REPORT.md locally |
| `push` | Reads | No | Writes | GCS delta sync + git push |
| `clean` | Deletes | No | No | Safe — GCS + PG are authoritative |
| `all` | Temp | Yes | Yes | Full pipeline |
| `list` | No | Yes | No | |
| `show` | No | Yes | No | |
| `search` | No | Yes | No | pgvector semantic search |
| `ask` | No | Yes | No | RAG synthesis (Phase 4) |
| `discover` | No | Yes | No | pgvector recommendations (Phase 4) |
| `graph` | No | Yes | No | Kuzu graph queries (Phase 3) |
| `annotate` | No | Yes | No | Immediate PG write |
| `stats` | No | Yes | No | |
| `orgs` | No | No | No | Edits config/orgs.yaml |
| `ontology` | No | No | No | Reads config/ontology.yaml |
| `profile` | No | No | No | Edits config/profile.yaml |
