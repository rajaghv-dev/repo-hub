# Scoring Algorithm

Every repo gets a **final score** between 0 and 100 composed of four independent sub-scores. The sub-scores are computed separately and then combined using configurable weights.

---

## Sub-scores

### S_activity — Activity (weight: 0.20)

Measures how alive and healthy the project is, independent of domain relevance.

```
recency   = max(0,  1 - days_since_last_push / 730)
            # linear decay over 2 years; archived repos → 0

star_vel  = stars / max(1, repo_age_days / 30)          # stars per month
star_score = log10(1 + star_vel) / log10(1 + 500)       # normalised; 500 stars/mo = 1.0

issue_sig = min(1.0, open_issues / 50)                  # 50+ open issues = active community

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

Measures how strongly a repo matches the ontology's signal definitions.

For each domain D:

```
topic_conf(D)    = matched_topics(D)    / total_signals.topics(D)
desc_conf(D)     = matched_desc_kw(D)   / total_signals.description(D)
dep_conf(D)      = matched_deps(D)      / total_signals.deps(D)
file_conf(D)     = matched_filenames(D) / total_signals.filenames(D)

domain_score(D) = 0.40 × topic_conf
                + 0.35 × desc_conf
                + 0.15 × dep_conf
                + 0.10 × file_conf

# A domain is assigned if domain_score(D) >= 0.15 (threshold in config)
assigned_domains = [D for D if domain_score(D) >= threshold]

S_ontology = max(domain_score(D) for D in assigned_domains)
             # best domain match, not sum (focused repos should not be penalised)
```

---

### S_deps — Dependency Match (weight: 0.20)

Measures how many recognisable tech-stack dependencies the repo uses, as extracted from its dependency files.

```
Files scraped (per repo):
  requirements.txt · requirements-*.txt
  pyproject.toml  · setup.cfg · setup.py
  CMakeLists.txt  (find_package / FetchContent)
  package.json    (dependencies + devDependencies)
  Cargo.toml      ([dependencies] section)
  go.mod          (require block)

dep_hits = count of extracted deps that appear in any domain's signals.deps list

S_deps = min(1.0, dep_hits / 10)
         # 10 matching deps = perfect score; configurable as dep_saturation
```

Only repos with **> 50 stars** have dep files scraped (configurable). Repos without scraped deps get S_deps = 0.

---

### S_profile — Profile Relevance (weight: 0.30)

Personalises the score to your declared interest profile in `config/profile.yaml`.

```
# For each assigned domain D:
domain_weight(D) = profile.domain_weights[D]    # 0.0–5.0, default 1.0

# Bonuses (additive, capped)
tech_bonus  = 0.20  if any matched tech_node is in profile.tech_interests
org_bonus   = 0.10  if repo.org in profile.priority_orgs

best_weight = max(domain_weight(D) for D in assigned_domains)
norm_weight = min(1.0, best_weight / 3.0)       # normalise to [0, 1]; 3.0 = max useful weight

S_profile = min(1.0, norm_weight + tech_bonus + org_bonus)
```

Setting a domain weight to `0.0` in your profile hard-excludes all repos in that domain from results.

---

## Composite Score

```
FINAL = W_activity × S_activity
      + W_ontology × S_ontology
      + W_deps     × S_deps
      + W_profile  × S_profile

Default weights:
  W_activity  = 0.20
  W_ontology  = 0.30
  W_deps      = 0.20
  W_profile   = 0.30
  (sum = 1.00)

Displayed as: round(FINAL × 100, 1)  →  score in [0.0, 100.0]
```

Weights are configurable in `config/profile.yaml` under `scoring_weights`.

---

## Hard Filters (applied before scoring)

Repos matching any of these conditions are excluded entirely:

| Filter | Config key |
|---|---|
| `is_fork == true` | `defaults.include_forks: false` |
| `stars < min_stars` | `defaults.min_stars: 10` |
| No OSI-approved license | `defaults.osi_only: true` |
| All assigned domain weights == 0.0 | profile.yaml |

---

## Score Explanation (`repo-hub show`)

Every repo carries a full `score_breakdown` in the database:

```json
{
  "score": 78.4,
  "s_activity": 0.81,
  "s_ontology": 0.72,
  "s_deps": 0.60,
  "s_profile": 0.90,
  "assigned_domains": ["ai_compiler", "gpu_runtime"],
  "matched_signals": {
    "ai_compiler": ["mlir (topic)", "MLIR (description)", "iree-compiler (dep)"],
    "gpu_runtime":  ["cuda (topic)", "*.cu (filename)"]
  },
  "extracted_deps": {
    "requirements.txt": ["torch", "iree-compiler", "iree-runtime"],
    "CMakeLists.txt":   ["CUDA", "LLVM", "MLIR"]
  }
}
```

`repo-hub show intel/llvm-project --explain` renders this as a rich panel in the terminal.

---

## Tuning the Score

Common adjustments in `config/profile.yaml`:

```yaml
# Boost compiler + GPU domains, reduce agentic
domain_weights:
  ai_compiler:   3.0
  gpu_runtime:   2.5
  quantization:  2.0
  agentic:       0.3   # still shows up, just ranked low

# Override composite weights if activity matters more to you
scoring_weights:
  W_activity: 0.30
  W_ontology: 0.25
  W_deps:     0.20
  W_profile:  0.25

# Declare your tech stack — boosts S_profile for matching repos
tech_interests:
  - mlir
  - rocm
  - triton
  - iree
  - onnxruntime

# Priority orgs get a small boost regardless of domain
priority_orgs:
  - openxla
  - iree-org
  - intel
  - tenstorrent
```
