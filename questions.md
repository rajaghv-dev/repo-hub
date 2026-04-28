# Ontology Improvement Questions

20 questions to refine the 21-domain ontology before implementation begins.
Answers will directly reshape domain boundaries, signal keywords, scoring weights, schema fields, and org coverage.

Answer as many or as few as useful — even partial answers on 5–6 will meaningfully change the design.
**Highest-impact:** Q5 (calibration repos), Q11 (search queries), Q19 (weakest signals), Q20 (annotation schema).

---

## Domain Coverage & Granularity

**Q1 — FPGA vs EDA split**
`fpga` (domain 5) covers FPGA *use* (inference, acceleration, gateware) and `eda_sim` (domain 6) covers the *tools* (Yosys, Verilator, Calyx). Your Alveo work involves both simultaneously — running HLS, simulating, then deploying. Should these be one domain, or is the current split how you actually think about them?

**Q2 — Missing "chip design" domain**
RTL-to-GDS flows (OpenLane, Magic, KLayout, sky130 PDK), analog design, and tapeout tooling don't fit cleanly into `eda_sim` (simulation/synthesis) or `soc_riscv` (generators). Do you work with full physical design flows enough to warrant a dedicated `chip_design` domain?

**Q3 — Real-time and embedded AI**
Zephyr RTOS is in `drivers_firmware`. Bare-metal embedded AI (TFLite Micro, Edge Impulse, CMSIS-NN, MCUXpresso), deterministic real-time scheduling, and sensor fusion have no clear home. Is embedded/real-time AI a gap that matters to your work?

**Q4 — Networking and data plane**
`interconnect` covers PCIe, CXL, NVMe, RDMA. SmartNICs (Bluefield, Pensando), P4 programmable data planes, DPDK offload, eBPF-based networking, and XDP arguably form a distinct "data plane" domain. Do you work with programmable network hardware enough to split this out?

**Q8 — AI compiler sub-domains**
`ai_compiler` spans graph compilers (TVM, XLA), kernel compilers (Triton), IR frameworks (MLIR), and hardware description compilers (CIRCT). These are conceptually very different. Does collapsing them into one domain lose information you need when browsing?

**Q14 — Simulation fidelity spectrum**
`eda_sim` has both fast RTL simulation (Verilator, cycle-accurate) and full-system simulation (gem5, Spike ISA sim, QEMU). These answer very different questions. Does the distinction between RTL simulation and system-level simulation matter for how you browse?

---

## Scoring & Calibration

**Q5 — Perfect score-100 repos** *(highest impact)*
Name 2–3 specific repos that you'd consider the most relevant to your current work — the ones you'd want at the absolute top of every `repo-hub list`. This calibrates whether the scoring formula and domain weights are tuned right.

**Q10 — Research vs production maturity**
`IST-DASLab/SparseGPT` is a research paper's code. `neuralmagic/DeepSparse` is production. Both are in `quantization`. Do you want a maturity signal so you can filter "only show me production-ready quantization tools"?

**Q13 — Dead but historically important repos**
Some repos are archived or 2+ years stale but are foundational references (early FPGA ML inference paper code, legacy HLS tools). Should there be a `historical` status that preserves them without polluting active scoring?

**Q16 — Geographic and consortium signals**
EU Chips Act, DARPA POSH/ERI, UK ARIA, CHIPS and Science Act repos, Horizon Europe hardware projects have strategic importance beyond star count. Do you want to track consortium/institutionally-funded open-source separately?

---

## Signal Quality

**Q7 — Heterogeneous compute dispatch layer**
OpenCL runtime, oneAPI Level Zero, SYCL runtimes, Vulkan Compute, ROCr/HSA sit between `gpu_runtime` and `hw_abstraction`. They're the dispatch layer between application and hardware. Does this scheduling/dispatch layer need its own signal cluster?

**Q11 — What do you search for that currently fails?** *(highest impact)*
Name 3 things you'd type into `repo-hub search` tomorrow if it existed. What queries would you expect a good answer to — and do you think the current ontology signals would surface the right repos?

**Q15 — The "glue" repos problem**
Bridging repos like `iree-org/iree`, `torch-mlir`, `onnxruntime` span 3+ domains but their *value* is precisely the bridging. Should there be a `bridge_adapter` tag or signal cluster for cross-domain integrators?

**Q19 — Most underserved domain signals** *(highest impact)*
Which of the 21 domains do you think has the weakest keyword coverage for your specific work? For example: `interconnect` signals focus on PCIe/NVMe but might miss CXL coherence protocols, GenZ, or OpenCAPI. Where would you expect the most misclassifications?

---

## Scope & Data Model

**Q6 — Security and trust**
Secure boot, TEEs (TrustZone, SEV-SNP), supply chain security (SBOM, Sigstore), HSMs, and firmware security analysis have no domain. Your SuryaOS and OpenTitan work touches this. Is security in scope?

**Q9 — Standards, specs, and working groups**
Khronos (OpenCL, SPIR-V, Vulkan), RISC-V International, PCI-SIG, CXL Consortium, Open Compute Project publish specs and reference implementations. Should specs be tracked differently from code repos? Do you care about them as a source type?

**Q12 — Cross-company collaboration as a signal**
Repos co-maintained by multiple chip vendors (LLVM, ROCm/HIP) are often more strategically important than single-vendor repos. Should joint-stewardship be a positive scoring signal?

**Q17 — Documentation, datasets, and benchmarks**
MLCommons benchmark suites, RISC-V spec repos, HuggingFace-only datasets. Are documentation-only repos, dataset repos, and benchmark definitions useful in your second brain, or do they create noise?

---

## Evolution & Annotation

**Q18 — Ontology evolution cadence**
MLIR added 3 new dialects in 6 months. CXL 3.0 and PCIe 6.0 are brand new. New quantization formats appear monthly. Is this something you'd revise quarterly, or do you want the tool to flag "this keyword cluster is outdated" automatically?

**Q20 — How do YOU annotate today?** *(highest impact)*
When you bookmark a repo manually right now, what do you record? The current `user_data` schema has: status, tags, notes, projects, priority. What's missing — "I tested this", "blocked on X", "waiting for release Y", "conflicts with Z in my stack", "contributor to watch"?

---

## Answer Space

| Q | Answer |
|---|---|
| Q1 | |
| Q2 | |
| Q3 | |
| Q4 | |
| Q5 | |
| Q6 | |
| Q7 | |
| Q8 | |
| Q9 | |
| Q10 | |
| Q11 | |
| Q12 | |
| Q13 | |
| Q14 | |
| Q15 | |
| Q16 | |
| Q17 | |
| Q18 | |
| Q19 | |
| Q20 | |
