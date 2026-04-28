# Five Better Ways to Build repo-hub

> Applied thinking frameworks: systems, critical, creative, first principles, and intuition.
> Each approach is a paradigm shift, not an incremental improvement.

---

## The Honest Critique First

The current design is a well-engineered **indexing system**. It fetches, classifies, scores, and stores. You browse a ranked list. This is useful — but it is solving a different problem than the one you actually have.

Your actual problem: **You operate at the intersection of 6+ fast-moving technical domains simultaneously. You cannot read everything. You need to know what matters, why it matters, how it connects to what you're building, and what you're about to miss.** A scored list does not answer any of those questions. It just reduces the pile.

The five approaches below each address a deeper version of the problem.

---

## Approach 1: The Ecosystem as a Living Knowledge Graph

**Thinking mode:** Systems thinking — model the whole, not the parts.

### The Core Insight

A score is a lossy compression of reality. It collapses all the relationships between repos into a single number and throws away the graph. But the graph *is* the knowledge.

Consider: `llvm/circt` (MLIR for hardware) depends on LLVM, targets the same FPGA backends as your Vitis HLS work, is contributed to by people at Intel and Google, and feeds into both `calyxir/calyx` (HLS IR) and IREE's hardware backends. A score of 73/100 tells you nothing about any of this. The graph tells you everything.

**First principles:** What is a second brain? It is a model of how things connect to each other and to you. A relational table with scores is not a model — it is a catalogue. A graph is a model.

### Architecture

```
Nodes (4 types):
  Repo        → id, name, org, score, domains
  Person      → github_login, affiliated_orgs, domain_tags
  Technology  → name, domain, aliases  (e.g. "MLIR", "ai_compiler")
  Paper       → arxiv_id, title, year, authors

Edges (directed, typed):
  Repo  -[DEPENDS_ON]→   Repo       (from dep_edges)
  Repo  -[IMPLEMENTS]→   Paper      (README citation extraction)
  Repo  -[TARGETS]→      Technology (from ontology classification)
  Person-[CONTRIBUTES_TO]→ Repo     (from GitHub contributor API)
  Person-[AFFILIATED_WITH]→ Org     (from GitHub profile)
  Tech  -[BUILT_ON]→     Tech       (e.g. ROCm BUILT_ON HIP BUILT_ON CUDA)
  Tech  -[ALTERNATIVE_TO]→ Tech     (ROCm ALTERNATIVE_TO CUDA)
```

**Implementation options (ranked):**

| Option | Complexity | Query power | Ops overhead |
|---|---|---|---|
| PostgreSQL recursive CTEs | Low | Medium | None |
| Apache AGE (PG extension) | Medium | High (Cypher) | Low |
| Neo4j AuraDB free tier | Medium | Very high | Low (managed) |
| Kuzu (embedded graph DB) | Low | High | None |

**Recommendation: Kuzu.** It is an embedded graph database (like SQLite but for graphs). No server. Python API. Runs in-process alongside your existing PostgreSQL. You build the graph in Kuzu locally, query it, then sync summaries back to PostgreSQL. Kuzu exports to Parquet — GCS-compatible.

```python
import kuzu
db = kuzu.Database("data/ecosystem.kuzu")
conn = kuzu.Connection(db)

# After classifying repos, build graph edges
conn.execute("""
    MATCH (a:Repo {id: $from_id}), (b:Repo {id: $to_id})
    CREATE (a)-[:DEPENDS_ON {dep_type: $dep_type}]->(b)
""", {"from_id": "pytorch/pytorch", "to_id": "NVIDIA/cutlass", "dep_type": "cmake"})

# Now answer questions the score system cannot
conn.execute("""
    MATCH path = (r:Repo {id: 'ucb-bar/chipyard'})-[:DEPENDS_ON*1..3]->(t:Repo)
    WHERE t.domain CONTAINS 'ai_compiler'
    RETURN t.id, t.score, length(path) AS hops
    ORDER BY hops, t.score DESC
""")
# → "What AI compiler repos is Chipyard transitively connected to?"
```

### What This Unlocks (Concrete to Your Work)

- **Gap detection:** "I use MLIR, ROCm, and LiteX — are there any repos that touch all three?" The graph answers this in one query. The score system cannot.
- **Influence analysis:** Which repos are the most-depended-upon in the AI compiler ecosystem? (`DEPENDS_ON` in-degree). These are the repos you cannot afford to miss a release of.
- **Convergence detection:** Two previously separate ecosystems (FPGA HLS and ML compilers) are being bridged by CIRCT. The graph shows this convergence emerging before any individual repo's score reflects it.
- **Your SuryaOS work:** "Which repos that KDE depends on also have NVIDIA or Intel contributors?" Maps the intersection of desktop and hardware vendor investment.

### Trade-offs

| Pro | Con |
|---|---|
| Answers relational questions scores cannot | Adds Kuzu as a dependency |
| Graph evolves — old edges tell you where the ecosystem came from | Contributor data requires 1 extra API call per repo |
| Kuzu is embedded — zero server ops | Paper extraction (IMPLEMENTS edges) requires DOI/arxiv parsing |

### Verdict

**Build this in phase 2, after basic scoring works.** The dep_edges table you already have is the seed. Once populated, add Kuzu sync as a post-classify step. The `repo-hub graph` command becomes your most powerful analytical tool.

---

## Approach 2: Replace the Keyword Ontology with an LLM Classification Pipeline

**Thinking mode:** Critical thinking — challenge the core assumption.

### The Core Insight

The keyword ontology is a 1990s solution to a 2025 problem. You are maintaining 18 × 50+ keyword lists and hoping that repo maintainers used the same vocabulary you did when writing their description.

They did not. `calyxir/calyx` doesn't mention "HLS" or "compiler" in its description — it says "an infrastructure language for composable, retargetable accelerator generators." `cocotb/cocotb` mentions "coroutines" not "simulation". The Alveo PCIe DMA kernel driver from Xilinx uses internal part numbers, not "PCIe" in its GitHub topics.

**The keyword ontology has systematically low recall for the domains you care most about: hardware, systems, and chip-adjacent software.** These communities do not write GitHub descriptions for discoverability. They write for people who already know the context.

**First principles:** What does classification actually require? Reading comprehension. Not pattern matching. An LLM has reading comprehension.

### Architecture

Replace `keyword_matcher.py` with `llm_classifier.py`:

```python
CLASSIFICATION_PROMPT = """
You are classifying a GitHub repository against a technical ontology.

ONTOLOGY (18 domains):
{ontology_summary}   ← cached in prompt cache, never re-sent

REPO TO CLASSIFY:
Name: {name}
Description: {description}
Topics: {topics}
Primary language: {language}
README excerpt (first 800 tokens): {readme_excerpt}
Dependencies found: {deps}

Return JSON:
{
  "primary_domain": "domain_id or null",
  "secondary_domains": ["domain_id", ...],
  "confidence": 0.0-1.0,
  "tech_nodes": ["specific technologies used"],
  "problem_solved": "one sentence: what problem does this solve?",
  "intended_user": "who is this for?",
  "search_terms": ["terms someone would search to find this"],
  "relevance_note": "one sentence: why this is or isn't relevant to OS/AI/FPGA/GPU inference work"
}
"""
```

**Cost model with Claude Haiku 4.5 + prompt caching:**

| Component | Tokens | Cost per repo |
|---|---|---|
| System + ontology (cached) | ~3,000 | $0.000075 (90% cache hit) |
| Repo content (input) | ~500 | $0.0000625 |
| Classification output | ~200 | $0.00025 |
| **Total per repo** | | **~$0.00033** |
| **10,000 repos** | | **~$3.30** |
| **Quarterly re-classification** | | **~$13.20/year** |

This is cheaper than your GCS storage costs.

**The `relevance_note` field is the killer feature.** Not just "this matches domain X" but "this is the upstream kernel driver for the PCIe DMA path your Alveo U50 uses." The LLM can make the connection between your profile and the repo in natural language.

### Hybrid Strategy

Don't eliminate the ontology — use it as the schema for the LLM's output and as a fallback for repos where LLM classification fails or is too expensive:

```
For repos with > 100 stars:    LLM classification (high quality)
For repos with 10-100 stars:   keyword matching (acceptable quality)
For repos with < 10 stars:     skip (below noise floor)
```

This limits LLM calls to ~3,000 repos (top tier), reducing cost to ~$1/run.

### What This Unlocks

- **Zero keyword maintenance.** The ontology becomes a prompt, not a YAML file. When a new paradigm emerges (say, "chiplet interconnect" as a new concept), you don't update keyword lists — the LLM already understands it.
- **Cross-domain synthesis.** The LLM will naturally identify that `llvm/circt` spans `fpga`, `ai_compiler`, and `eda_sim` in ways keyword matching won't.
- **The `relevance_note` field** — a per-repo sentence explaining why it matters to *your* specific work — is the highest-value output in the entire system. No keyword system can produce this.
- **FPGA/HLS repos.** Repos like `ferrandi/PandA-bambu` ("Bambu HLS"), `calyxir/calyx`, `pymtl/pymtl3` use domain-specific jargon that the LLM understands fluently.

### Trade-offs

| Pro | Con |
|---|---|
| Far higher recall and precision | Requires Anthropic API key + billing |
| `relevance_note` is qualitatively different output | Non-deterministic (same repo, slightly different result each run) |
| Zero maintenance as vocabulary evolves | Rate limiting for large batches (use Anthropic Batch API) |
| Handles all 6 file formats of dep analysis natively | LLM can hallucinate tech_nodes not actually in the repo |

**Mitigation for hallucination:** The `tech_nodes` field is validated against the actual dep_edges. If the LLM says "uses CUDA" but no CUDA dep was found in the dep files, flag it as `unverified`.

### Verdict

**This is the highest-leverage change in the entire system.** The ontology as a prompt is strictly superior to the ontology as keyword lists for your domain. Use the Anthropic SDK with prompt caching. Use Batch API for the initial 10k-repo run (50% cost reduction, async). Run incrementally on new repos only after that.

---

## Approach 3: Event-Driven Pulse Architecture

**Thinking mode:** Systems thinking — model the ecosystem as a living system, not a static dataset.

### The Core Insight

The ecosystem does not change once a week. It pulses continuously. A new Xilinx FPGA kernel driver appears on a Tuesday morning. The IREE team tags a major release Wednesday afternoon. An Intel researcher publishes an ArXiv preprint on Thursday that becomes the basis of a new repo 3 months later. A weekly batch job sees none of this in real time.

**The second brain should have the same tempo as the ecosystem it models.**

Two distinct processes with different cadences:

```
PULSE (hourly, lightweight, no token needed):
  → GitHub org events via Atom feeds
  → Release feeds per tracked repo  
  → ArXiv RSS from tracked institutional authors
  → HuggingFace "new this week" API
  → Writes "signals" to a queue

FULL PIPELINE (weekly, heavyweight, uses all tokens):
  → Processes accumulated signals
  → Re-classifies new and changed repos
  → Refreshes scores
  → Pushes to PG, GCS, GitHub
```

### Architecture

**Signal sources (all free, no token, real-time):**

| Source | URL Pattern | What it gives you |
|---|---|---|
| GitHub org events | `https://github.com/{org}/events.atom` | New repos, new forks, pushes |
| GitHub releases | `https://github.com/{org}/{repo}/releases.atom` | Version tags with changelogs |
| ArXiv categories | `https://rss.arxiv.org/rss/cs.AR+cs.LG` | cs.AR (hardware arch) + cs.LG (ML) |
| HuggingFace new models | `https://huggingface.co/models?sort=created` (API) | New model repos |

**Signal schema:**

```sql
CREATE TABLE signals (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT,          -- github_events|github_release|arxiv|huggingface
    org          TEXT,
    repo_id      TEXT,          -- may be NULL for new repos not yet in DB
    signal_type  TEXT,          -- new_repo|new_release|new_paper|star_spike
    payload      JSONB,         -- raw signal data
    processed    BOOLEAN DEFAULT FALSE,
    detected_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**The pulse process** (runs as a lightweight cron, no GPU, no model loading):

```python
# ~50 lines of code, runs in <30 seconds
for org in tracked_orgs:
    feed = parse_atom(f"https://github.com/{org}/events.atom")
    for event in feed.entries:
        if event.type == "CreateEvent" and event.payload.ref_type == "repository":
            # New repo in a tracked org — immediate signal
            db.insert_signal(source="github_events", org=org,
                             signal_type="new_repo", payload=event.payload)
```

**Why ArXiv matters for your work:** Hardware architects at Intel, AMD, Google publish papers 6–12 months before releasing the code. `cs.AR` (Computer Architecture and Hardware Design) is the direct feed. A paper titled "Efficient PCIe DMA for ML Accelerators" from an Xilinx researcher is the leading indicator of a future repo. Tracking this makes repo-hub a pre-cognitive system, not a reactive one.

### What This Unlocks

- **For your FPGA work:** New Xilinx repos appear the same day they're created, not next week.
- **For LLM inference:** vLLM releases a new version with paged attention improvements — you know within the hour, not after your next weekly browse.
- **For AI compilers:** An ArXiv paper from the CIRCT team on a new FIRRTL lowering pass tells you what the next LLVM/CIRCT release will contain before it ships.
- **For SuryaOS:** A KDE Plasma release note appears in the KDE events feed — surface it to your `desktop_open` watchlist immediately.

### Trade-offs

| Pro | Con |
|---|---|
| Near-real-time awareness of the ecosystem | Pulse process needs to run continuously (cron or small always-on process) |
| Zero token cost for pulse (pure RSS/Atom) | ArXiv matching requires heuristic author → org mapping |
| ArXiv gives 6–12 month lead time on repos | Signal noise — not every new repo is relevant |

**Signal noise mitigation:** New repos from tracked orgs with zero stars get a 48h hold before classification. If they reach 10 stars in 48h (viral), classify immediately. Otherwise, process in the next weekly run.

### Verdict

**Build the pulse process as a standalone 50-line script first.** It can run as a simple cron job outputting to a `signals` table. The weekly full pipeline then processes `WHERE processed = FALSE`. This is the most operationally low-risk of the five approaches — it adds value without changing the core pipeline.

---

## Approach 4: Contributor Intelligence as the Early Warning System

**Thinking mode:** Creative thinking + Intuition — the most important signal is invisible to the current design.

### The Core Insight

The current design tracks **repos**. But repos are trailing indicators. The leading indicator is **people**.

Consider: Phitchaya Mangpo Phothilimthana led the development of IREE at Google. When she moved to a new role, the people tracking IREE's commit log knew before any announcement. The engineer who wrote the Triton compiler's core transformation passes is the single most important person in the GPU kernel compiler ecosystem. When they start a new project — even with 2 stars and a vague description — it is worth your attention.

**Intuition:** In a field this specialised, 50 people are responsible for 80% of the fundamental work. Tracking those 50 people is worth more than tracking 10,000 repos.

### Architecture

```sql
-- New tables
CREATE TABLE contributors (
    github_login     TEXT PRIMARY KEY,
    display_name     TEXT,
    affiliated_orgs  JSONB DEFAULT '[]',   -- inferred from profile + repos
    domain_tags      JSONB DEFAULT '[]',   -- inferred from repos contributed to
    h_index_proxy    REAL DEFAULT 0,       -- weighted sum of contributed repo scores
    last_seen_at     TIMESTAMPTZ
);

CREATE TABLE contributor_repo_edges (
    github_login  TEXT REFERENCES contributors(github_login),
    repo_id       TEXT REFERENCES repos(id),
    commits       INTEGER DEFAULT 0,
    first_commit  TIMESTAMPTZ,
    last_commit   TIMESTAMPTZ,
    is_maintainer BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (github_login, repo_id)
);
```

**How contributor data is collected (GitHub API):**

```python
# For each classified repo with score > 60:
contributors = github.get(f"/repos/{org}/{repo}/contributors?per_page=30")
for c in contributors:
    upsert_contributor(c.login)
    upsert_edge(c.login, repo_id, c.contributions)

# For each contributor, fetch their recent public repos:
user_repos = github.get(f"/users/{login}/repos?sort=created&per_page=10")
for r in user_repos:
    if r not in known_repos:
        # New repo from a domain expert — surface immediately
        emit_signal("contributor_new_repo", login=login, repo=r)
```

**The `h_index_proxy`** scores contributors by the weighted average score of repos they've contributed to. A person who has contributed to LLVM, MLIR, IREE, and ROCm has a high proxy score — they are a node worth watching. When they create something new, it surfaces automatically.

### Killer Feature: Cross-Org Contributor Tracking

```sql
-- Find contributors who work across your most important domain boundaries
SELECT c.github_login, c.domain_tags,
       ARRAY_AGG(DISTINCT r.org) AS orgs
FROM contributors c
JOIN contributor_repo_edges e ON e.github_login = c.github_login
JOIN repos r ON r.id = e.repo_id
WHERE r.assigned_domains && '["fpga", "ai_compiler"]'   -- spans both domains
GROUP BY c.github_login, c.domain_tags
HAVING COUNT(DISTINCT r.org) >= 3    -- works at 3+ orgs
ORDER BY c.h_index_proxy DESC;
```

This query finds the people who are actively bridging FPGA and AI compiler work across organisations. These people are the convergence points of your most important technical domains. Following them is better than following any individual repo.

### What This Unlocks

- **Pre-star signal:** A Xilinx compiler engineer creates a new repo on Saturday with 0 stars. By Monday morning, `repo-hub digest` flags it because you track that contributor's work on Vitis HLS.
- **Ecosystem convergence:** When Intel engineers start appearing in the IREE contributor list and IREE engineers appear in the ROCm issue tracker, you know these communities are converging before any blog post says so.
- **For your FPGA/HLS work:** The 8 people who maintain LiteX, cocotb, and the Xilinx open-source kernel drivers are the community. When one of them forks something or creates a new project, you should know.
- **For your SuryaOS work:** KDE Plasma maintainers who also contribute to Mesa and Wayland are the people defining the Linux graphics stack you depend on. Their new projects are high-signal.

### Trade-offs

| Pro | Con |
|---|---|
| Pre-star signal — see important repos before they're famous | GitHub API rate limit: 30 contributors per repo × 10k repos = 300k extra calls. Needs token + throttling |
| Reveals human connections code deps don't show | Privacy-adjacent — tracking individual engineers feels invasive |
| `h_index_proxy` is a better domain expertise signal than star counts | Contributor data changes slowly — monthly refresh is sufficient |

**Privacy note:** All data is public GitHub activity. But store only what's necessary: login, affiliated orgs (inferred from profile), repos contributed to, commit counts. No email, no private data. This is the same data GitHub displays publicly.

### Verdict

**Build contributor tracking for your top 200 repos (score > 70) first.** This costs ~6,000 API calls (200 repos × 30 contributors), well within the 5,000/hr token limit. The contributor graph from those 200 repos will surface the 100–200 people who matter most in your ecosystem. Run monthly. New repo detection from those contributors runs in the hourly pulse.

---

## Approach 5: The Ecosystem Answers Your Questions — RAG over the Knowledge Base

**Thinking mode:** First principles + Intuition — what are you actually trying to accomplish?

### The Core Insight

**First principles question:** Why do you need a second brain?

Not to have a scored list of repos. That's a means. The end is: **to know what to build with, what to learn, what to watch, and what you're about to miss — without spending 4 hours a week reading GitHub.**

A scored list requires you to read and synthesize. A second brain should synthesize for you.

The fundamental capability missing from the current design is **synthesis across multiple repos in response to a specific question.** No browse command, no `--domain` filter, no score threshold answers: *"What are my options for doing PCIe DMA from user space to an Alveo FPGA card, and which ones have active maintenance?"*

RAG (Retrieval-Augmented Generation) answers that question by retrieving the relevant repo chunks and synthesizing an answer.

### Architecture

```
Query: "PCIe DMA from user space to Alveo FPGA"
    ↓
Hybrid retrieval:
  → pgvector semantic search on repo_embeddings (top-K by cosine similarity)
  → PostgreSQL FTS: to_tsquery('pcie & dma & fpga & userspace')
  → RRF (Reciprocal Rank Fusion) to merge both result sets
    ↓
Context assembly:
  → Top 8 repos: name + description + README excerpt + your notes + score + domains
  → Your profile context: "User works on Alveo U50/U55C, SuryaOS, KDE"
    ↓
Claude synthesis (with citations):
  "For PCIe DMA from user space to Alveo FPGA cards, the main options are:
   1. XDMA kernel driver (Xilinx/dma_ip_drivers) — official Xilinx driver,
      actively maintained, supports scatter-gather DMA...
   2. SPDK (spdk/spdk) — user-space NVMe/PCIe driver framework...
   3. LitePCIe (enjoy-digital/litepcie) — if building custom FPGA gateware..."
```

**The retrieval corpus** is everything already in your system:
- Repo metadata + README excerpts (already embedded via bge-small)
- Your personal annotations and notes (embedded as additional documents)
- Digest events (recent changes, new releases)
- The `relevance_note` field from Approach 2 (LLM-generated per-repo summaries)

**Your notes become part of the retrieval index.** When you annotate `spdk/spdk` with "check DPDK integration for Alveo PCIe path", that note becomes retrievable context that informs future answers about PCIe on FPGAs.

### CLI interface

```bash
# Natural language query
repo-hub ask "What are my options for PCIe DMA on Alveo FPGA?"
repo-hub ask "Which MLIR dialects target AMD GPU backends?"
repo-hub ask "What changed in the ROCm ecosystem this month?"
repo-hub ask "Which repos would be most useful for my SuryaOS AI integration work?"

# With constraints
repo-hub ask "inference engines for quantized LLMs" --domain llm_inference --min-stars 1000
repo-hub ask "FPGA HLS tools" --active-only --language C++

# Synthesis mode — compare options
repo-hub compare vllm-project/vllm lm-sys/sglang --question "production inference serving"
```

### Hybrid Retrieval (why both FTS and vector)

Neither alone is sufficient:
- **Vector search** finds semantic matches ("speculative execution in inference" matches repos that use "draft models" without containing the exact phrase)
- **FTS** finds exact technical terms ("PCIe", "DMA", "AXI4") that vector search sometimes misses if the embedding space compresses them away

**RRF fusion:**

```python
def reciprocal_rank_fusion(vector_results, fts_results, k=60):
    scores = {}
    for rank, doc in enumerate(vector_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank + 1)
    for rank, doc in enumerate(fts_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### What This Unlocks

This is the only approach that changes what the second brain *is*, not just how it works.

| Before | After |
|---|---|
| `repo-hub list --domain fpga --min-score 60` → you read 30 repos | `repo-hub ask "FPGA HLS tools for inference"` → synthesized answer with 5 specific recommendations |
| Weekly digest tells you 12 repos changed | `repo-hub ask "what changed this week that matters for my KDE/GPU work?"` → curated synthesis |
| You remember seeing a PCIe DMA repo somewhere | `repo-hub ask "that PCIe DMA repo I noted last month"` → retrieved from your annotations |

### Trade-offs

| Pro | Con |
|---|---|
| Answers questions, not just returns lists | Requires Claude API (but you can use prompt caching, Batch API) |
| Your annotations feed back into retrieval — the brain grows | Answer quality depends on retrieval quality — hallucination risk |
| No new infrastructure — pgvector already handles retrieval | Cost: ~$0.01 per `ask` query with claude-haiku. Acceptable for personal use |
| Works with existing embeddings | Claude context window limits how many repos you can synthesize at once |

**Cost model:** 8 retrieved repos × ~800 tokens each = 6,400 tokens context + 500 token output = ~$0.03 per query with claude-sonnet-4-6. At 20 queries/week = ~$0.60/week = $31/year. Less than a coffee per week for a system that synthesizes your entire technical ecosystem.

### Verdict

**This is the endgame of the second brain concept.** Everything else (fetch, classify, embed, score, annotate) is infrastructure for this. The synthesis layer transforms repo-hub from a tool that manages information into a tool that generates knowledge. Build it after the indexing pipeline is solid. The pgvector foundation is already designed for it.

---

## Implementation Sequence (Synthesis of All Five)

The five approaches are not competing alternatives. They are layers of the same system, buildable in sequence:

```
Phase 1 — Foundation (current design, validated)
  ├── fetch + classify (keyword ontology, then migrate to LLM — Approach 2)
  ├── score + embed (bge-small → pgvector)
  ├── annotate + browse (list, show, annotate)
  └── push/restore cycle (GCS + PostgreSQL portability)

Phase 2 — Intelligence
  ├── Pulse architecture (hourly Atom/RSS watcher — Approach 3)
  ├── Contributor tracking (top-200 repos → people graph — Approach 4)
  └── LLM classification for top repos (Approach 2)

Phase 3 — Graph
  └── Kuzu knowledge graph (dep_edges + contributor_edges + tech_nodes — Approach 1)

Phase 4 — Synthesis
  └── RAG query interface (repo-hub ask — Approach 5)
```

Each phase is independently valuable. Each phase builds on the previous. None requires abandoning what came before.

---

## New Domains: HLS, Simulation, PCIe, SoC

Three domains missing from the current 18:

| ID | Label | What it covers |
|---|---|---|
| `eda_sim` | EDA & Simulation | RTL simulation (Verilator, cocotb, GHDL, Icarus), synthesis (Yosys), formal verification (SymbiYosys), waveform tools (GTKWave), FPGA toolchains (nextpnr, F4PGA, prjtrellis) |
| `interconnect` | Interconnect & Storage | PCIe, CXL, NVMe, RDMA (libfabric, rdma-core), high-speed serial, SPDK, NVMe-cli, LitePCIe, verilog-pcie, DMA engines |
| `soc_riscv` | SoC & RISC-V | SoC generators (Chipyard, LiteX), RISC-V cores (CVA6, CV32E40P, Rocket, BOOM), chip design flows (Hammer, OpenTitan), simulation (Spike ISA sim), RISC-V ISA |

## New Orgs: HLS, Simulation, PCIe, SoC

**EDA / Simulation / HLS**

| Handle | Type | What they own |
|---|---|---|
| `YosysHQ` | org | Yosys synthesis, nextpnr P&R, SymbiYosys formal, fpga-toolchain |
| `cocotb` | org | cocotb RTL verification framework + AXI/I2C/Ethernet bus models |
| `verilator` | org | Verilator (fast SystemVerilog/Verilog simulator) |
| `ghdl` | org | GHDL VHDL 2008/93/87 simulator |
| `steveicarus` | user | Icarus Verilog |
| `calyxir` | org | Calyx IR — intermediate language for accelerator generators |
| `ferrandi` | user | PandA-Bambu HLS framework (Politecnico di Milano) |
| `llvm` | org | CIRCT — MLIR-based hardware compiler infrastructure (already tracked) |
| `pymtl` | org | PyMTL3 — Python hardware modelling, simulation, and verification |
| `UCSBarchlab` | org | PyRTL — Python RTL design language |
| `lnis-uofu` | org | OpenFPGA — FPGA architecture exploration and silicon proofs |
| `f4pga` | org | F4PGA — fully open-source FPGA toolchain (rebranded SymbiFlow) |
| `enjoy-digital` | user | LiteX SoC framework, LitePCIe, LiteEth, LiteICLink |
| `litex-hub` | org | LiteX board support, peripheral cores |
| `gatecat` | user | prjoxide (Lattice 28nm FPGA), prjtrellis |
| `alexforencich` | user | Verilog PCIe, Ethernet, AXI cores — cocotb extension models |

**PCIe / CXL / Interconnect**

| Handle | Type | What they own |
|---|---|---|
| `spdk` | org | SPDK — user-space NVMe/PCIe storage performance dev kit |
| `ofiwg` | org | libfabric — OpenFabrics high-speed network fabrics (RDMA, OPA) |
| `linux-nvme` | org | nvme-cli — NVMe management CLI |
| `linux-rdma` | org | rdma-core — RDMA userspace libraries and verbs |
| `pmem` | org | PMDK — Persistent Memory Development Kit, SPDK fork |

**SoC / RISC-V**

| Handle | Type | What they own |
|---|---|---|
| `chipsalliance` | org | CHIPS Alliance: Chisel, FIRRTL, Rocket Chip, F4PGA |
| `openhwgroup` | org | OpenHW: CV32E40P (32-bit RV32), CVA6 (64-bit RV64), CORE-V verification |
| `ucb-bar` | org | UC Berkeley: Chipyard SoC framework, BOOM OOO core, Hammer VLSI flow |
| `pulp-platform` | org | ETH Zurich PULP: CVA6, Cheshire Linux-capable SoC, Bender dependency tool |
| `lowrisc` | org | OpenTitan silicon root of trust, ibex RISC-V core |
| `riscv` | org | RISC-V International: ISA manual, opcodes, specs |
| `riscv-boom` | org | Berkeley Out-of-Order Machine (superscalar RV64GC) |
| `riscv-software-src` | org | Spike ISA simulator, riscv-tests, riscv-pk |

---

## The Unifying Principle

Each of the five approaches addresses the same underlying gap: **the current design models repos as independent objects. The ecosystem is not a collection of independent objects. It is a system of relationships — between code, people, organisations, standards, and ideas.**

The knowledge graph (Approach 1) models the code relationships.
The contributor intelligence (Approach 4) models the people relationships.
The pulse architecture (Approach 3) models the time relationships.
The LLM classifier (Approach 2) models the semantic relationships (what this repo means in context).
The RAG interface (Approach 5) is what you get when all four relationship types are queryable together.

The second brain becomes useful not when it has all the repos, but when it understands how they connect.
