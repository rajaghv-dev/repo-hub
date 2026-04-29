# repo-hub

> A second brain for the open-source ecosystem — track, classify, score, and annotate repos from chip companies, AI labs, OS projects, hardware toolchains, and ML frameworks so you always know what matters, how it connects, and what you're about to miss.

## Core principle: the machine is disposable, the data is not

Clone on any machine → run the full pipeline → push all state to cloud → wipe local → repeat anywhere.

```bash
git clone https://github.com/rajaghv-dev/repo-hub
cd repo-hub
cp .env.example .env   # fill in 4 tokens: GITHUB_TOKEN, HF_TOKEN, DATABASE_URL, REPO_HUB_GCS_BUCKET
pip install -e .
repo-hub doctor        # verify all connections
repo-hub db init       # run schema.sql (first time only)
repo-hub all --clean   # full pipeline + wipe local data
```

All state lives in three cloud stores: **PostgreSQL** (repos, scores, vectors, your annotations), **GCS** (raw cache, Parquet exports), and **GitHub** (code, config, auto-generated report). The local `data/` directory is always safe to delete.

---

## What it does

`repo-hub` monitors **~95 GitHub organisations** and HuggingFace Hub across hardware, AI, OS, and systems software. It:

1. **Fetches** every public OSI-licensed repo from tracked orgs
2. **Classifies** against a 21-domain ontology (keyword matching → LLM classification in phase 2)
3. **Scores** for relevance to your personal interest profile
4. **Embeds** descriptions via `bge-small` → `pgvector` for semantic search
5. **Annotates** — you mark repos as `bookmarked / in-use / dismissed` with notes
6. **Digests** — tells you what's new or changed since last run
7. **Answers** — `repo-hub ask "PCIe DMA on Alveo FPGA"` synthesises across the full corpus

---

## 21 Domains

### Hardware Foundation
| # | ID | Label |
|---|---|---|
| 1 | `os_kernel` | OS & Kernel |
| 2 | `drivers_firmware` | Drivers & Firmware |
| 3 | `desktop_open` | Open Desktop (KDE · GNOME · Wayland) |
| 4 | `android_device` | Android & Devices |
| 5 | `fpga` | FPGA |
| 6 | `eda_sim` | EDA & Simulation |
| 7 | `interconnect` | Interconnect & Storage (PCIe · CXL · NVMe · RDMA) |
| 8 | `soc_riscv` | SoC & RISC-V |

### Compute Engines
| # | ID | Label |
|---|---|---|
| 9 | `cpu_inference` | CPU Inference & Kernels |
| 10 | `gpu_runtime` | GPU Runtimes (CUDA · ROCm · SYCL) |
| 11 | `ai_compiler` | AI Compilers & Frameworks |

### AI/ML Stack
| # | ID | Label |
|---|---|---|
| 12 | `quantization` | Quantization & Compression |
| 13 | `llm_inference` | LLM Inference |
| 14 | `ml_training` | ML Training |
| 15 | `hf_ecosystem` | HuggingFace Ecosystem |
| 16 | `hw_abstraction` | Hardware Abstraction |

### Infrastructure
| # | ID | Label |
|---|---|---|
| 17 | `profiling` | Profiling & Benchmarking |
| 18 | `databases` | Databases & Vector Stores |
| 19 | `browser_wasm` | Browser & WebAssembly |
| 20 | `agentic` | Agentic Systems |
| 21 | `observability` | Telemetry · Tracing · Observability |

---

## CLI Commands

```bash
# Setup & health
repo-hub doctor             # verify GitHub token, HF token, PG, GCS, embedding model
repo-hub db init            # run schema.sql on fresh PostgreSQL instance

# Full pipeline
repo-hub all                # fetch + classify + embed + score + push
repo-hub all --clean        # same, then delete data/ when done
repo-hub all --incremental  # only process new/changed repos

# Data collection
repo-hub fetch              # GitHub API → GCS cache
repo-hub hf                 # HuggingFace Hub → GCS cache
repo-hub pulse              # one-shot RSS/Atom/ArXiv signal scan (lightweight, no token)

# Classification & scoring
repo-hub classify           # ontology match → PostgreSQL
repo-hub embed              # bge-small embeddings → pgvector
repo-hub score              # composite scores → PostgreSQL

# Browse & query
repo-hub list               # [--domain] [--org] [--min-score] [--status] [--sort] [--format]
repo-hub show  ORG/REPO     # full detail: scores, signals, deps, your notes, --explain
repo-hub search QUERY       # pgvector semantic search across all repos
repo-hub ask   QUESTION     # RAG synthesis: retrieves + synthesises an answer with citations
repo-hub discover           # "more like my bookmarks" — pgvector recommendations
repo-hub graph  ORG/REPO    # knowledge graph: dependencies, contributors, connected repos

# Annotation (writes to PostgreSQL)
repo-hub annotate ORG/REPO  # --status --tags --note --project --priority

# Sync & maintenance
repo-hub restore            # pull GCS cache to local data/
repo-hub push               # sync GCS + git push REPORT.md
repo-hub clean              # delete data/ (safe — everything is in cloud)
repo-hub digest             # what's new/changed since last run [--since Nd] [--domain]
repo-hub stats              # domain distribution, top orgs, score histogram
repo-hub export             # [--format json|csv|parquet|markdown] [--output FILE]

# Configuration
repo-hub orgs               # list / add / remove orgs
repo-hub ontology           # list / show / validate domains
repo-hub profile            # show / init / set-weight
```

---

## Storage

| Store | Technology | What lives there |
|---|---|---|
| **Data plane** | PostgreSQL (Supabase/Neon) | Repos, scores, pgvector embeddings, dep graph, annotations, contributors, signals |
| **Blob store** | GCS | Raw API cache, dep files, model cards, Parquet exports |
| **Control plane** | GitHub | Code, config, ontology, profile, `REPORT.md` (auto-generated weekly) |
| **Local** | `data/` (temp) | Scratch only — always safe to delete |

---

## Installation

```bash
pip install -e .          # installs repo_hub package + repo-hub CLI entry point
pip install -e ".[dev]"   # + pytest/coverage for development
```

**Required secrets** (set in `.env`):
| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | GitHub API — 5000 req/hr vs 60 without |
| `HF_TOKEN` | HuggingFace Hub API (optional but higher limits) |
| `DATABASE_URL` | PostgreSQL connection string (Neon / Supabase / local Docker) |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCS service account JSON path |
| `REPO_HUB_GCS_BUCKET` | GCS bucket name |

## Implementation Status

| Phase | Status | What it adds |
|---|---|---|
| **1 — Foundation** | **Implemented** | Fetch · keyword classify · score · embed · annotate · push/restore |
| **2 — Intelligence** | Planned | Hourly pulse watcher · contributor tracking · LLM classification |
| **3 — Graph** | Planned | Kuzu knowledge graph · dep edges · `repo-hub graph` |
| **4 — Synthesis** | Planned | RAG · `repo-hub ask` · `repo-hub discover` |

See [better.md](better.md) for the full rationale behind each phase.

---

## Docs

| File | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Component diagram, DB schema, GCS layout, embedding strategy, phase model |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Machine lifecycle, setup, pipeline, GitHub Actions schedule |
| [docs/ONTOLOGY.md](docs/ONTOLOGY.md) | 21-domain taxonomy with signal keywords, cross-domain relationships |
| [docs/ORGS.md](docs/ORGS.md) | All ~95 tracked orgs grouped by category |
| [docs/SCORING.md](docs/SCORING.md) | Sub-score formulas, hardware domain weighting, tuning guide |
| [better.md](better.md) | 5 alternative implementation approaches with full rationale |
| [schema.sql](schema.sql) | PostgreSQL DDL — run once on a fresh instance |

---

## Quick Start Queries

```bash
repo-hub list --domain eda_sim --min-score 60 --sort score
repo-hub list --domain fpga --domain interconnect --active --top 30
repo-hub search "MLIR-based compiler targeting AMD GPU"
repo-hub ask  "What open-source tools exist for PCIe DMA from user space?"
repo-hub ask  "What changed in the ROCm ecosystem this month?"
repo-hub discover                                    # based on your bookmarks
repo-hub digest --since 7d --domain soc_riscv
```
