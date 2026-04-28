# repo-hub

> A second brain for the open-source ecosystem — track, classify, score, and annotate repos from chip companies, AI labs, OS projects, and ML frameworks so you always know what's worth watching.

## Core principle: the machine is disposable, the data is not

Clone on any machine → run the full pipeline → push all state to cloud → wipe local → repeat anywhere.

```
git clone → pip install -e . → .env (4 tokens) → repo-hub all --clean
```

All state lives in three cloud stores: **PostgreSQL** (repos, scores, vectors, your annotations), **GCS** (raw cache, Parquet exports), and **GitHub** (code, config, auto-generated report). The local `data/` directory is always safe to delete.

## What it does

`repo-hub` monitors ~75 GitHub organisations and HuggingFace Hub orgs across hardware, AI, OS, and systems software. It classifies every public repo against a structured ontology of 18 technical domains, scores each for relevance to your work, stores embeddings for semantic search, and tracks your personal annotations — all in PostgreSQL accessible from any machine.

## Domains (18)

| # | ID | Label |
|---|---|---|
| 1 | `os_kernel` | OS & Kernel |
| 2 | `drivers_firmware` | Drivers & Firmware |
| 3 | `desktop_open` | Open Desktop (KDE · GNOME · Wayland) |
| 4 | `android_device` | Android & Devices |
| 5 | `fpga` | FPGA |
| 6 | `cpu_inference` | CPU Inference & Kernels |
| 7 | `gpu_runtime` | GPU Runtimes (CUDA · ROCm · SYCL) |
| 8 | `ai_compiler` | AI Compilers & Frameworks |
| 9 | `quantization` | Quantization & Compression |
| 10 | `llm_inference` | LLM Inference |
| 11 | `ml_training` | ML Training |
| 12 | `hf_ecosystem` | HuggingFace Ecosystem |
| 13 | `hw_abstraction` | Hardware Abstraction |
| 14 | `profiling` | Profiling & Benchmarking |
| 15 | `databases` | Databases & Vector Stores |
| 16 | `browser_wasm` | Browser & WebAssembly |
| 17 | `agentic` | Agentic Systems |
| 18 | `observability` | Telemetry · Tracing · Observability |

## CLI Commands

```bash
repo-hub fetch              # pull GitHub API data for all orgs, scrape dep files
repo-hub classify           # run ontology matching + scoring → write to SQLite
repo-hub list               # browse repos  [--domain] [--org] [--min-score] [--status] [--sort] [--format]
repo-hub show  ORG/REPO     # full detail: scores, matched signals, deps, your notes
repo-hub annotate ORG/REPO  # set status (bookmarked/in-use/dismissed), tags, notes
repo-hub digest             # what's new or changed since last run
repo-hub stats              # domain distribution, top orgs, score histogram
repo-hub export             # JSON / CSV / Markdown / Parquet
repo-hub sync               # push/pull SQLite and cache to/from GCS
repo-hub hf                 # HuggingFace Hub: list/download model cards and datasets
repo-hub orgs               # manage org registry
repo-hub ontology           # inspect / validate taxonomy
repo-hub profile            # manage your interest profile and domain weights
```

## Data Flow

```
GitHub API ──► fetch ──► GCS cache ──► classify ──► PostgreSQL
                                           │               │
HuggingFace Hub ───────────────────────────┘         pgvector (embed)
                                                           │
                                              list · search · annotate · digest
```

## Storage

| Store | Technology | What lives there |
|---|---|---|
| **Data plane** | PostgreSQL (Supabase/Neon) | Repos, scores, pgvector embeddings, dep graph, annotations |
| **Blob store** | GCS | Raw API cache, dep files, Parquet exports |
| **Control plane** | GitHub | Code, config, ontology, profile, `REPORT.md` |
| **Local** | `data/` (temp) | Scratch only — always safe to delete |

## Docs

- [Architecture & Tech Design](docs/ARCHITECTURE.md) — component diagram, DB schema, GCS layout, embedding strategy
- [Workflow — Machine Lifecycle](docs/WORKFLOW.md) — setup, full pipeline, GitHub Actions schedule
- [Ontology — 18 Domains](docs/ONTOLOGY.md) — domain taxonomy with signal keywords
- [Organisations (~75)](docs/ORGS.md) — all tracked orgs grouped by category
- [Scoring Algorithm](docs/SCORING.md) — sub-scores, formula, tuning

## Quick Reference

```bash
repo-hub doctor                          # verify all connections
repo-hub restore                         # pull GCS cache → local
repo-hub all --clean                     # full pipeline, wipe local after
repo-hub list --domain ai_compiler       # browse by domain
repo-hub search "MLIR inference engine"  # semantic search (pgvector)
repo-hub annotate ORG/REPO --status bookmarked --note "..."
repo-hub digest --since 7d              # what changed this week
repo-hub export --format parquet        # export to GCS
```

## Status

Design complete — implementation in progress.
