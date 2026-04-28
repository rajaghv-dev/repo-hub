# repo-hub

> A second brain for the open-source ecosystem — track, classify, score, and annotate repos from chip companies, AI labs, OS projects, and ML frameworks so you always know what's worth watching.

## What it does

`repo-hub` continuously monitors ~75 GitHub organisations across hardware, AI, and systems software. It classifies every public repo against a structured ontology of 18 technical domains, scores each one for relevance to your work, and stores everything in a queryable local database backed by GCS. You annotate repos you care about, run a digest to see what changed, and export reports.

It is not a dashboard. It runs as a CLI, stores locally, and syncs to the cloud.

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
GitHub API ──► fetch ──► JSON cache (local + GCS)
                              │
HuggingFace Hub ─────────────┤
                              ▼
                         classify
                    (ontology · deps · profile)
                              │
                              ▼
                         SQLite DB  ◄──► GCS sync
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
              annotate              list / digest / export
           (your second brain)
```

## Storage

| Layer | Technology | Purpose |
|---|---|---|
| API cache | JSON files | Raw GitHub API responses, 24h TTL |
| Working DB | SQLite | Scored repos + your annotations, fast local queries |
| Object store | GCS | Durable cache, DB backups, large exports, Parquet snapshots |
| Model/dataset | HuggingFace Hub | Model cards, dataset metadata, HF repo cross-reference |

## Docs

- [Architecture & Tech Design](docs/ARCHITECTURE.md)
- [Ontology — 18 Domains](docs/ONTOLOGY.md)
- [Organisations (~75)](docs/ORGS.md)
- [Scoring Algorithm](docs/SCORING.md)

## Status

Design phase — implementation in progress.
