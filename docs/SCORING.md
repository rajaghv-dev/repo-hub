# Scoring Algorithm

Every repo gets a **final score** between 0 and 100 composed of four independent sub-scores. Sub-scores are computed separately and combined using configurable weights.

---

## Sub-scores

### S_activity — Activity (weight: 0.20)

Measures how alive and healthy the project is, independent of domain relevance.

```
recency   = max(0, 1 - days_since_last_push / 730)
            # linear decay over 2 years; archived repos → 0

star_vel  = stars / max(1, repo_age_days / 30)        # stars per month
star_score = log10(1 + min(star_vel, 1000)) / log10(1001)
             # clamped at 1000 stars/mo to handle viral repos

issue_sig = min(1.0, open_issues / 50)

S_activity = 0.50 × recency + 0.35 × star_score + 0.15 × issue_sig
```

| Condition | Approx S_activity |
|---|---|
| Pushed this week, 10k stars | ~0.90 |
| Pushed last month, 500 stars | ~0.72 |
| Pushed 6 months ago, 200 stars | ~0.52 |
| Pushed 18 months ago, 50 stars | ~0.22 |
| Archived | 0.00 |

---

### S_ontology — Domain Match (weight: 0.30)

Measures how strongly a repo matches the ontology's signal definitions. Signal weights differ by domain group — hardware repos rarely set GitHub topics.

#### Standard signal weights (AI/ML + Infrastructure domains)

| Signal source | Weight |
|---|---|
| Topics | 0.40 |
| Description | 0.35 |
| Deps | 0.15 |
| Filenames | 0.10 |

#### Hardware domain signal weights

Applies to: `os_kernel` · `drivers_firmware` · `fpga` · `eda_sim` · `interconnect` · `soc_riscv`

| Signal source | Weight | Rationale |
|---|---|---|
| Topics | **0.15** | Hardware repos rarely set GitHub topics |
| Description | **0.40** | Description is the most reliable text signal |
| Deps | **0.10** | C/C++ build deps are harder to parse reliably |
| Filenames | **0.35** | File extensions (*.v, *.sv, *.cu, *.dts) are the strongest signal |

#### Per-domain confidence formula

```
topic_conf(D)    = matched_topics(D)    / total_signals.topics(D)
desc_conf(D)     = matched_desc_kw(D)   / total_signals.description(D)
dep_conf(D)      = matched_deps(D)      / total_signals.deps(D)
file_conf(D)     = matched_filenames(D) / total_signals.filenames(D)

domain_score(D) = W_topics  × topic_conf
                + W_desc    × desc_conf
                + W_deps    × dep_conf
                + W_files   × file_conf
                # where W_* come from the domain's group (standard or hardware)

assigned_domains = [D for D if domain_score(D) >= 0.15]   # threshold configurable
S_ontology = max(domain_score(D) for D in assigned_domains)
```

---

### S_deps — Dependency Match (weight: 0.20)

Measures how many recognisable tech-stack dependencies the repo uses, extracted from dependency files.

```
Files scraped (repos with > 50 stars):
  requirements.txt · requirements-*.txt
  pyproject.toml  · setup.cfg · setup.py
  CMakeLists.txt  (find_package / FetchContent calls)
  package.json    (dependencies + devDependencies)
  Cargo.toml      ([dependencies] section)
  go.mod          (require block)

dep_hits = count of extracted deps matching any domain's signals.deps list

S_deps = min(1.0, dep_hits / dep_saturation)
```

**Per-domain dep saturation** (hits needed for full score):

| Domain group | Saturation | Rationale |
|---|---|---|
| Hardware (`eda_sim`, `fpga`, `soc_riscv`, `interconnect`) | 3 | C/C++ projects have few Python-parseable deps |
| Compute (`gpu_runtime`, `cpu_inference`, `ai_compiler`) | 6 | Mix of Python and C++ deps |
| AI/ML (`quantization`, `llm_inference`, `ml_training`, `hf_ecosystem`) | 12 | Python-heavy, many detectable deps |
| Infrastructure (`databases`, `agentic`, `observability`) | 10 | Standard |

Only repos with **> 50 stars** have dep files scraped (configurable via `dep_scrape_min_stars` in `config/orgs.yaml`). Repos without scraped deps get S_deps = 0.

---

### S_profile — Profile Relevance (weight: 0.30)

Personalises the score to your declared interest profile in `config/profile.yaml`.

```
domain_weight(D) = profile.domain_weights[D]    # 0.0–5.0, default 1.0

tech_bonus  = 0.20  if any matched tech_node is in profile.tech_interests
org_bonus   = 0.10  if repo.org in profile.priority_orgs
lang_bonus  = 0.05  if repo.language in profile.preferred_languages

best_weight = max(domain_weight(D) for D in assigned_domains)
norm_weight = min(1.0, best_weight / 3.0)

S_profile = min(1.0, norm_weight + tech_bonus + org_bonus + lang_bonus)
```

Setting a domain weight to `0.0` **hard-excludes** all repos in that domain.

---

## Composite Score

```
FINAL = W_activity × S_activity
      + W_ontology × S_ontology
      + W_deps     × S_deps
      + W_profile  × S_profile

Default weights (must sum to 1.0):
  W_activity  = 0.20
  W_ontology  = 0.30
  W_deps      = 0.20
  W_profile   = 0.30

Displayed as: round(FINAL × 100, 1)   →  score in [0.0, 100.0]
```

Weights are overridable in `config/profile.yaml` under `scoring_weights`.

---

## Hard Filters (applied before scoring)

Repos matching any condition below are excluded entirely and never scored:

| Filter | Config key |
|---|---|
| `is_fork == true` | `defaults.include_forks: false` |
| `stars < min_stars` | `defaults.min_stars: 10` |
| No OSI-approved license | `defaults.osi_only: true` |
| License not detected but stars < 100 | Heuristic — large repos often lack detected licenses |
| All assigned domain weights == 0.0 | `profile.domain_weights` |

**License note:** GitHub license detection fails on ~25% of repos that are genuinely open source. Repos with `stars > 100` and `license: null` are passed through for manual review rather than silently excluded.

---

## Score Explanation

Every classified repo stores a full breakdown accessible via `repo-hub show ORG/REPO --explain`:

```json
{
  "score": 81.2,
  "s_activity": 0.84,
  "s_ontology": 0.76,
  "s_deps": 0.67,
  "s_profile": 0.95,
  "assigned_domains": ["eda_sim", "ai_compiler", "fpga"],
  "primary_domain": "eda_sim",
  "matched_signals": {
    "eda_sim":     ["rtl-simulation (topic)", "synthesis (desc)", "sim_main.cpp (file)"],
    "ai_compiler": ["mlir (topic)", "MLIR dialect (desc)", "iree-compiler (dep)"],
    "fpga":        ["fpga (topic)", "*.xdc (file)"]
  },
  "extracted_deps": {
    "CMakeLists.txt": ["LLVM", "MLIR", "CIRCT"],
    "requirements.txt": ["cocotb", "pymtl3"]
  },
  "activity_detail": {
    "days_since_push": 12,
    "star_velocity_monthly": 120,
    "open_issues": 34
  }
}
```

---

## Phase 2: LLM Classification

In phase 2, `S_ontology` for repos with > 100 stars is replaced by an LLM-generated classification using Claude Haiku with prompt caching:

```
LLM output (replaces S_ontology for top repos):
  primary_domain     → replaces keyword domain match
  secondary_domains  → replaces multi-domain assignment
  confidence         → replaces domain_score formula
  tech_nodes         → validated against dep_edges
  relevance_note     → "why this matters for your work" (new field, no keyword equivalent)
  problem_solved     → stored in repos table, searchable
  search_terms       → added to FTS index
```

Cost: ~$0.00033 per repo → ~$3 for 10,000 repos per run (quarterly). Use Anthropic Batch API for 50% cost reduction on the initial bulk classification.

---

## Tuning Your Profile

Edit `config/profile.yaml` to adjust what scores high:

```yaml
# Boost hardware/compiler domains, reduce agentic/browser
domain_weights:
  eda_sim:      3.0   # very important for FPGA toolchain work
  fpga:         3.0
  interconnect: 2.8   # PCIe/NVMe work
  soc_riscv:    2.5
  ai_compiler:  2.8   # MLIR/Triton/IREE
  gpu_runtime:  2.8   # CUDA/ROCm
  os_kernel:    2.5
  agentic:      0.5   # less important
  browser_wasm: 0.8

# Override composite weights
scoring_weights:
  W_activity:  0.20
  W_ontology:  0.30
  W_deps:      0.20
  W_profile:   0.30

# Declare your tech stack — boosts S_profile
tech_interests:
  - mlir
  - circt
  - iree
  - rocm
  - triton
  - verilator
  - cocotb
  - litex
  - spdk

# Priority orgs
priority_orgs:
  - openxla
  - iree-org
  - llvm        # for CIRCT
  - YosysHQ
  - cocotb
  - chipsalliance
  - enjoy-digital
```
