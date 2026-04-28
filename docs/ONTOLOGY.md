# Ontology — 21 Domains

The ontology is the backbone of classification. Every repo is matched against all 21 domains using four signal types: **GitHub topics**, **description text**, **dependency file contents**, and **filename presence**. A repo can belong to multiple domains.

Signal weights are not uniform. Hardware and systems domains (`os_kernel`, `drivers_firmware`, `fpga`, `eda_sim`, `interconnect`, `soc_riscv`) use **reduced topic weight** because hardware repos rarely set GitHub topics. See [Signal Weighting](#signal-weighting).

---

## Domain Index

| # | ID | Group | Label | Core Technologies |
|---|---|---|---|---|
| 1 | `os_kernel` | Hardware | OS & Kernel | Linux, eBPF, io_uring, DPDK, FreeBSD |
| 2 | `drivers_firmware` | Hardware | Drivers & Firmware | Mesa, EDK2, coreboot, Zephyr, U-Boot |
| 3 | `desktop_open` | Hardware | Open Desktop | KDE, GNOME, Wayland, Qt, GTK |
| 4 | `android_device` | Hardware | Android & Devices | AOSP, LineageOS, GrapheneOS, postmarketOS |
| 5 | `fpga` | Hardware | FPGA | Vitis HLS, OpenCL/FPGA, RTL, RISC-V softcores |
| 6 | `eda_sim` | Hardware | EDA & Simulation | Yosys, Verilator, cocotb, GHDL, Calyx, Bambu HLS |
| 7 | `interconnect` | Hardware | Interconnect & Storage | PCIe, CXL, NVMe, RDMA, SPDK, libfabric, LitePCIe |
| 8 | `soc_riscv` | Hardware | SoC & RISC-V | Chipyard, CVA6, Rocket, BOOM, OpenTitan, LiteX |
| 9 | `cpu_inference` | Compute | CPU Inference & Kernels | SIMD, AMX, AVX-512, ARM SVE, VNNI, oneDNN |
| 10 | `gpu_runtime` | Compute | GPU Runtimes | CUDA, ROCm/HIP, SYCL, Metal, Vulkan Compute |
| 11 | `ai_compiler` | Compute | AI Compilers & Frameworks | MLIR, TVM, XLA, Triton, IREE, torch.compile |
| 12 | `quantization` | AI/ML | Quantization & Compression | GPTQ, AWQ, GGUF, INT8/INT4/FP8, pruning, distillation |
| 13 | `llm_inference` | AI/ML | LLM Inference | vLLM, llama.cpp, TensorRT-LLM, SGLang |
| 14 | `ml_training` | AI/ML | ML Training | PyTorch, JAX, DeepSpeed, Megatron, FSDP |
| 15 | `hf_ecosystem` | AI/ML | HuggingFace Ecosystem | Transformers, Diffusers, PEFT, TRL, Accelerate |
| 16 | `hw_abstraction` | AI/ML | Hardware Abstraction | ONNX Runtime, OpenVINO, QNN/SNPE, CoreML, Olive |
| 17 | `profiling` | Infra | Profiling & Benchmarking | MLPerf, NSight, VTune, perf, flamegraphs |
| 18 | `databases` | Infra | Databases & Vector Stores | Milvus, Qdrant, DuckDB, LanceDB, FAISS, pgvector |
| 19 | `browser_wasm` | Infra | Browser & WebAssembly | WebGPU, WebNN, Wasmtime, WasmEdge, WASI |
| 20 | `agentic` | Infra | Agentic Systems | LangChain, LlamaIndex, AutoGen, MCP, CrewAI |
| 21 | `observability` | Infra | Telemetry · Tracing · Observability | OpenTelemetry, Prometheus, MLflow, DVC, Evidently |

---

## Group 1 — Hardware Foundation (Domains 1–8)

---

### 1. OS & Kernel

**Description:** Operating system kernels, kernel subsystems, kernel-space tooling, system programming primitives, and Linux-adjacent infrastructure.

**Tech nodes:** Linux kernel · FreeBSD · OpenBSD · eBPF · BCC · bpftrace · libbpf · io_uring · DPDK · systemd · perf · kprobes · cgroups · namespaces

| Signal source | Keywords |
|---|---|
| Topics | `linux` · `kernel` · `ebpf` · `bpf` · `io-uring` · `dpdk` · `operating-system` · `freebsd` · `kprobes` · `cgroups` · `namespaces` · `system-programming` |
| Description | `kernel` · `eBPF` · `io_uring` · `syscall` · `kprobe` · `tracepoint` · `cgroup` · `namespace` · `DPDK` · `packet processing` · `kernel module` · `scheduler` · `memory management` |
| Deps | `bcc` · `bpftrace` · `pyroute2` · `dpdk` · `liburing` |
| Filenames | `*.bpf.c` · `*.ko` · `Kconfig` · `vmlinux.h` · `kernel/` |

---

### 2. Drivers & Firmware

**Description:** GPU and device drivers, UEFI/BIOS firmware, bootloaders, RTOS, BSPs, device trees, and embedded firmware stacks.

**Tech nodes:** Mesa (amdgpu · i915 · nouveau) · EDK2/UEFI · coreboot · U-Boot · Zephyr RTOS · OpenEmbedded · Yocto · STM32 HAL · device tree · libdrm · DRM/KMS

| Signal source | Keywords |
|---|---|
| Topics | `driver` · `firmware` · `uefi` · `bios` · `bootloader` · `rtos` · `device-tree` · `embedded` · `mesa` · `drm` · `hal` · `bsp` · `zephyr` · `u-boot` · `coreboot` |
| Description | `driver` · `firmware` · `DRM` · `KMS` · `UEFI` · `bootloader` · `device tree` · `board support` · `BSP` · `HAL` · `register map` · `peripheral` · `interrupt` |
| Deps | `libdrm` · `libusb` · `libudev` |
| Filenames | `*.dts` · `*.dtsi` · `*.inf` · `*.asl` · `edk2.conf` · `zephyr.yaml` |

---

### 3. Open Desktop

**Description:** Desktop environments, display servers, compositors, window managers, and the foundational freedesktop.org stack — Wayland, X11, D-Bus, XDG.

**Tech nodes:** KDE Plasma · KWin · GNOME Shell · Mutter · Wayland · Weston · Sway · Hyprland · Qt · GTK · D-Bus · XDG · PipeWire · PulseAudio · Flatpak

| Signal source | Keywords |
|---|---|
| Topics | `kde` · `gnome` · `wayland` · `x11` · `compositor` · `desktop-environment` · `window-manager` · `qt` · `gtk` · `dbus` · `freedesktop` · `flatpak` · `plasma` · `pipewire` |
| Description | `desktop` · `Wayland` · `compositor` · `KDE` · `GNOME` · `window manager` · `D-Bus` · `Qt` · `GTK` · `XDG` · `display server` · `Plasma` |
| Deps | `PyQt5` · `PyQt6` · `PyGObject` · `dbus-python` |
| Filenames | `*.qml` · `*.ui` · `*.glade` · `org.*.xml` · `*.desktop` |

---

### 4. Android & Devices

**Description:** Android OS forks, AOSP components, Android graphics stack, mobile Linux distributions, and device-specific repositories.

**Tech nodes:** AOSP · LineageOS · GrapheneOS · postmarketOS · Android HAL · Skia · Vulkan on Android · Treble · ART runtime · Ubuntu Touch · CalyxOS

| Signal source | Keywords |
|---|---|
| Topics | `android` · `aosp` · `lineageos` · `grapheneos` · `postmarketos` · `mobile` · `hal` · `android-app` · `treble` · `art` |
| Description | `Android` · `AOSP` · `HAL` · `Treble` · `ART` · `Dalvik` · `mobile` · `device-specific` |
| Deps | `android-sdk` |
| Filenames | `Android.mk` · `Android.bp` · `AndroidManifest.xml` · `*.aidl` · `sepolicy/` |

---

### 5. FPGA

**Description:** FPGA toolchains, HLS, RTL, soft-core processors, FPGA inference engines, and FPGA-accelerated compute. Closely related to `eda_sim` (domain 6) which covers the EDA tools used with FPGAs.

**Tech nodes:** Vitis HLS · Vivado · OpenCL for FPGA · RISC-V softcores · LiteX · nMigen · Chisel · Amaranth · OpenFPGA · VexRiscv · Rocketchip · AIE (AI Engines)

| Signal source | Keywords |
|---|---|
| Topics | `fpga` · `hls` · `rtl` · `verilog` · `vhdl` · `xilinx` · `intel-fpga` · `risc-v` · `chisel` · `hardware-design` · `digital-design` · `systemverilog` · `alveo` · `aie` |
| Description | `FPGA` · `HLS` · `RTL` · `Verilog` · `VHDL` · `bitstream` · `LUT` · `synthesis` · `place and route` · `timing closure` · `soft core` · `Alveo` · `AI Engine` |
| Deps | `pyrtl` · `migen` · `amaranth-hdl` · `cocotb` · `pynq` |
| Filenames | `*.v` · `*.sv` · `*.vhd` · `*.xdc` · `*.tcl` · `*.bit` · `hls.tcl` · `vivado.tcl` · `*.xo` |

---

### 6. EDA & Simulation

**Description:** Electronic Design Automation toolchains, RTL simulation, logic synthesis, place-and-route, formal verification, HLS compilers (non-vendor), and open FPGA toolchains. The tooling layer beneath domain 5 (FPGA).

**Tech nodes:** Yosys · nextpnr · SymbiYosys · Verilator · cocotb · GHDL · Icarus Verilog · Calyx IR · Bambu HLS · PyMTL3 · PyRTL · OpenFPGA · F4PGA · prjtrellis · prjoxide · GTKWave · CIRCT

| Signal source | Keywords |
|---|---|
| Topics | `eda` · `rtl-simulation` · `synthesis` · `verilator` · `cocotb` · `yosys` · `formal-verification` · `place-and-route` · `hls` · `ghdl` · `icarus` · `logic-simulation` · `hardware-compiler` |
| Description | `RTL simulation` · `synthesis` · `place and route` · `formal verification` · `HLS` · `hardware simulation` · `testbench` · `waveform` · `timing analysis` · `netlist` · `EDA` · `logic gate` |
| Deps | `cocotb` · `pyrtl` · `pymtl3` · `migen` · `amaranth-hdl` |
| Filenames | `*.v` · `*.sv` · `*.vhd` · `*.fir` · `*.futil` · `sim_main.cpp` · `*.gtkw` · `Makefile` (cocotb pattern) |

---

### 7. Interconnect & Storage

**Description:** High-speed serial interconnects (PCIe, CXL, NVMe, RDMA), DMA engines, storage performance toolkits, fabric libraries, and low-level device access from user space.

**Tech nodes:** PCIe · CXL · NVMe · RDMA · SPDK · libfabric · rdma-core · nvme-cli · LitePCIe · verilog-pcie · DPDK (PCIe path) · UCX · AXI DMA · PMDK · io_uring (storage path)

| Signal source | Keywords |
|---|---|
| Topics | `pcie` · `cxl` · `nvme` · `rdma` · `spdk` · `dma` · `interconnect` · `fabric` · `infiniband` · `storage` · `user-space-driver` · `axi` · `high-bandwidth` |
| Description | `PCIe` · `CXL` · `NVMe` · `RDMA` · `DMA` · `fabric` · `InfiniBand` · `user-space` · `zero-copy` · `scatter-gather` · `IOMMU` · `BAR` · `MMIO` · `AXI4` |
| Deps | `spdk` · `libfabric` · `pyverbs` |
| Filenames | `pcie_driver.c` · `dma_engine.v` · `nvme.c` · `spdk.conf` · `*.axi4` · `xdma/` |

---

### 8. SoC & RISC-V

**Description:** SoC generators, RISC-V processor cores, chip design frameworks, VLSI flows, ISA simulation, and open silicon initiatives.

**Tech nodes:** Chipyard · Rocket Chip · BOOM · CVA6 · CV32E40P · LiteX · OpenTitan · ibex · Hammer VLSI · Spike ISA simulator · Bender · Chisel · FIRRTL · Cheshire · VeeR EL2

| Signal source | Keywords |
|---|---|
| Topics | `risc-v` · `soc` · `processor` · `chisel` · `firrtl` · `riscv` · `chipyard` · `rocket-chip` · `boom` · `cva6` · `opentitan` · `litex` · `vlsi` · `tapeout` · `open-silicon` |
| Description | `RISC-V` · `SoC` · `processor core` · `Chisel` · `FIRRTL` · `chip generator` · `VLSI` · `tapeout` · `RTL-to-GDS` · `ISA simulator` · `out-of-order` · `superscalar` |
| Deps | `chisel` · `firrtl` · `pymtl3` · `riscv-tools` |
| Filenames | `*.scala` · `*.fir` · `config/` (Chipyard) · `Makefrag` · `vlsi/` · `sky130/` · `build.mill` |

---

## Group 2 — Compute Engines (Domains 9–11)

---

### 9. CPU Inference & Kernels

**Description:** Optimised CPU-side inference libraries, SIMD kernel implementations, quantised inference on CPU, and CPU math primitives.

**Tech nodes:** SIMD (AVX-512 · AVX2 · AMX · ARM SVE · ARM NEON) · VNNI · oneDNN · BLIS · OpenBLAS · Eigen · xsimd · highway · llama.cpp (CPU path) · neural-speed

| Signal source | Keywords |
|---|---|
| Topics | `simd` · `avx` · `avx512` · `amx` · `arm-neon` · `arm-sve` · `cpu-inference` · `onednn` · `openblas` · `cpu-optimization` · `intrinsics` |
| Description | `SIMD` · `AVX-512` · `AMX` · `NEON` · `SVE` · `intrinsics` · `vectorization` · `oneDNN` · `BLAS` · `gemm` · `quantized` · `CPU inference` |
| Deps | `highway` · `xsimd` · `openblas` · `mkl` · `onednn` |
| Filenames | `*.avx2.cpp` · `*.avx512.cpp` · `*_neon.cpp` · `*_sve.cpp` · `kernels/` |

---

### 10. GPU Runtimes

**Description:** GPU programming models, runtime libraries, kernel libraries, and cross-vendor GPU abstraction layers.

**Tech nodes:** CUDA · cuBLAS · cuDNN · CUTLASS · ROCm · HIP · rocBLAS · MIOpen · SYCL · oneAPI · DPC++ · Metal · Vulkan Compute · WebGPU (native) · OpenCL

| Signal source | Keywords |
|---|---|
| Topics | `cuda` · `rocm` · `hip` · `sycl` · `opencl` · `gpu` · `oneapi` · `metal` · `vulkan-compute` · `gpgpu` · `hpc` · `parallel-computing` · `cutlass` |
| Description | `CUDA` · `ROCm` · `HIP` · `SYCL` · `GPU kernel` · `warp` · `thread block` · `shared memory` · `stream` · `cuBLAS` · `rocBLAS` · `heterogeneous` |
| Deps | `cupy` · `pycuda` · `pyopencl` · `hip-python` · `intel-extension-for-pytorch` |
| Filenames | `*.cu` · `*.cuh` · `*.hip` · `*.cl` · `*.metal` · `*.hlsl` |

---

### 11. AI Compilers & Frameworks

**Description:** ML compilers, graph IR frameworks, kernel compilers, model optimisation passes, and compute graph transformation toolchains.

**Tech nodes:** MLIR · LLVM · TVM · XLA · StableHLO · PJRT · Triton · IREE · Halide · torch.compile · TorchScript · ONNX graph transforms · Glow · Relax · Linalg dialect · torch-mlir · CIRCT (hardware compilers)

| Signal source | Keywords |
|---|---|
| Topics | `mlir` · `compiler` · `tvm` · `llvm` · `xla` · `triton` · `iree` · `halide` · `graph-optimization` · `jit` · `aot` · `ir` · `codegen` · `stablehlo` · `circt` |
| Description | `MLIR` · `compiler` · `intermediate representation` · `IR` · `lowering` · `codegen` · `JIT` · `AOT` · `kernel fusion` · `graph optimization` · `dialect` · `affine` · `linalg` |
| Deps | `apache-tvm` · `iree-compiler` · `iree-runtime` · `torch-mlir` · `triton` |
| Filenames | `*.mlir` · `*.td` · `*.inc` · `CMakeLists.txt` |

---

## Group 3 — AI/ML Stack (Domains 12–16)

---

### 12. Quantization & Compression

**Description:** Model quantisation (post-training and QAT), pruning, weight sharing, knowledge distillation, sparsity, and compressed model formats.

**Tech nodes:** GPTQ · AWQ · GGUF · GGML · bitsandbytes · INT8 · INT4 · FP8 · SparseGPT · Marlin kernels · AutoAWQ · neural-compressor · Olive · DeepSparse · SparseML · QLoRA

| Signal source | Keywords |
|---|---|
| Topics | `quantization` · `pruning` · `compression` · `distillation` · `sparsity` · `gptq` · `awq` · `gguf` · `int8` · `int4` · `fp8` · `mixed-precision` · `sparse` |
| Description | `quantization` · `INT8` · `INT4` · `FP8` · `pruning` · `sparsity` · `distillation` · `GPTQ` · `AWQ` · `GGUF` · `bitsandbytes` · `calibration` · `weight compression` |
| Deps | `bitsandbytes` · `auto-gptq` · `autoawq` · `neural-compressor` · `optimum` · `quanto` |
| Filenames | `quantize.py` · `calibrate.py` · `prune.py` · `*.gguf` |

---

### 13. LLM Inference

**Description:** Inference engines specifically optimised for large language models — batching, paged attention, speculative decoding, quantised weight loading, and serving stacks.

**Tech nodes:** vLLM · llama.cpp · TensorRT-LLM · ExLlamaV2 · Ollama · MLC-LLM · lmdeploy · SGLang · text-generation-inference · ctransformers

| Signal source | Keywords |
|---|---|
| Topics | `llm` · `inference` · `vllm` · `llama-cpp` · `tensorrt-llm` · `text-generation` · `serving` · `paged-attention` · `continuous-batching` · `speculative-decoding` |
| Description | `LLM inference` · `paged attention` · `continuous batching` · `speculative decoding` · `KV cache` · `token generation` · `throughput` · `TTFT` · `TPS` |
| Deps | `vllm` · `llama-cpp-python` · `ctransformers` · `mlc-llm` · `lmdeploy` |
| Filenames | `serve.py` · `engine.py` · `scheduler.py` |

---

### 14. ML Training

**Description:** Training frameworks, distributed training infrastructure, optimisers, gradient handling, and training orchestration.

**Tech nodes:** PyTorch · TensorFlow · JAX · Flax · DeepSpeed · Megatron-LM · FSDP · Horovod · torchrun · Lightning · NeMo · Composer

| Signal source | Keywords |
|---|---|
| Topics | `training` · `deep-learning` · `pytorch` · `tensorflow` · `jax` · `deepspeed` · `megatron` · `fsdp` · `distributed-training` · `optimizer` · `fine-tuning` |
| Description | `training` · `backpropagation` · `gradient` · `optimizer` · `loss` · `epoch` · `distributed training` · `data parallel` · `model parallel` · `mixed precision` |
| Deps | `torch` · `tensorflow` · `jax` · `flax` · `deepspeed` · `lightning` · `composer` |
| Filenames | `train.py` · `finetune.py` · `pretrain.py` · `trainer.py` |

---

### 15. HuggingFace Ecosystem

**Description:** Libraries, tools, and models that are part of or tightly integrated with the HuggingFace open-source stack.

**Tech nodes:** Transformers · Diffusers · PEFT · TRL · Accelerate · Datasets · Tokenizers · Evaluate · Gradio · Hub · Optimum · safetensors · text-generation-inference

| Signal source | Keywords |
|---|---|
| Topics | `huggingface` · `transformers` · `diffusers` · `peft` · `trl` · `accelerate` · `safetensors` · `datasets` · `gradio` · `optimum` |
| Description | `transformers` · `HuggingFace` · `model hub` · `pipeline` · `AutoModel` · `AutoTokenizer` · `safetensors` · `LoRA` · `PEFT` · `TRL` · `RLHF` |
| Deps | `transformers` · `diffusers` · `peft` · `trl` · `accelerate` · `datasets` · `evaluate` · `gradio` · `optimum` · `safetensors` |
| Filenames | `config.json` · `tokenizer_config.json` · `model.safetensors` |

---

### 16. Hardware Abstraction

**Description:** Cross-hardware portability layers, execution provider plugins, and vendor-neutral inference APIs that sit above raw GPU/NPU/CPU programming.

**Tech nodes:** ONNX Runtime · OpenVINO · QNN (Qualcomm Neural Network) · SNPE · CoreML · TFLite delegates · Olive · ExecuTorch · NNAPI · DirectML · TVM runtime

| Signal source | Keywords |
|---|---|
| Topics | `onnx` · `onnxruntime` · `openvino` · `qnn` · `snpe` · `coreml` · `tflite` · `npu` · `delegate` · `execution-provider` · `neural-engine` |
| Description | `ONNX Runtime` · `OpenVINO` · `execution provider` · `EP` · `QNN` · `SNPE` · `CoreML` · `TFLite delegate` · `NPU` · `neural engine` · `hardware-agnostic` |
| Deps | `onnxruntime` · `onnxruntime-gpu` · `openvino-dev` · `coremltools` · `tensorflow-lite` |
| Filenames | `*.onnx` · `model.xml` · `model.bin` · `*.mlpackage` · `*.tflite` |

---

## Group 4 — Infrastructure (Domains 17–21)

---

### 17. Profiling & Benchmarking

**Description:** Performance measurement, hardware counter access, tracing, roofline analysis, ML benchmark suites, and visualisation tools.

**Tech nodes:** MLPerf · NSight Systems · NSight Compute · VTune · perf · flamegraph · bpftrace (perf context) · likwid · PAPI · sysstat · torch.profiler · TensorBoard profiler

| Signal source | Keywords |
|---|---|
| Topics | `profiling` · `benchmarking` · `tracing` · `perf` · `mlperf` · `nsight` · `vtune` · `flamegraph` · `performance` · `hardware-counters` |
| Description | `profiler` · `benchmark` · `latency` · `throughput` · `roofline` · `trace` · `flamegraph` · `ops/sec` · `FLOPS` · `bandwidth` · `PMU` · `hardware counter` |
| Deps | `torch_tb_profiler` · `pyinstrument` · `scalene` · `py-spy` · `pyperf` |
| Filenames | `benchmark.py` · `bench.py` · `profile.py` · `mlperf.conf` · `*.nsys-rep` |

---

### 18. Databases & Vector Stores

**Description:** Vector databases, AI-native datastores, columnar/analytical engines, embedding indexes, and approximate nearest-neighbour libraries.

**Tech nodes:** Milvus · Qdrant · Weaviate · ChromaDB · LanceDB · pgvector · DuckDB · Apache Arrow · FAISS · ScaNN · hnswlib · Vespa

| Signal source | Keywords |
|---|---|
| Topics | `vector-database` · `embeddings` · `similarity-search` · `ann` · `faiss` · `qdrant` · `milvus` · `weaviate` · `duckdb` · `columnar` · `arrow` · `retrieval` · `rag` |
| Description | `vector database` · `embedding` · `similarity search` · `ANN` · `HNSW` · `IVF` · `cosine similarity` · `retrieval` · `RAG` · `columnar` |
| Deps | `faiss-cpu` · `faiss-gpu` · `qdrant-client` · `pymilvus` · `chromadb` · `lancedb` · `duckdb` · `pyarrow` · `weaviate-client` |
| Filenames | `*.lance` · `*.parquet` · `*.arrow` · `index.faiss` |

---

### 19. Browser & WebAssembly

**Description:** Browser engines, WebGPU/WebNN for in-browser AI inference, WebAssembly runtimes, and WASM-based cross-platform compute.

**Tech nodes:** Chromium · V8 · WebKit · Gecko · WebGPU · WebNN · Wasmtime · WasmEdge · WASI · Cranelift · Emscripten · wasm-bindgen · ONNX.js

| Signal source | Keywords |
|---|---|
| Topics | `webgpu` · `webnn` · `webassembly` · `wasm` · `browser` · `wasmtime` · `wasmedge` · `wasi` · `javascript-engine` · `v8` · `rendering-engine` |
| Description | `WebGPU` · `WebNN` · `WebAssembly` · `WASM` · `browser` · `JavaScript engine` · `V8` · `Cranelift` · `WASI` · `in-browser inference` · `edge inference` |
| Deps | `wasmtime` · `wasmer` · `emscripten` |
| Filenames | `*.wasm` · `*.wat` · `*.wit` · `CMakeLists.txt` (with emscripten) |

---

### 20. Agentic Systems

**Description:** Agent frameworks, multi-agent orchestration, memory systems, tool-use infrastructure, and the Model Context Protocol (MCP) ecosystem.

**Tech nodes:** LangChain · LangGraph · LlamaIndex · AutoGen · CrewAI · Haystack · Mem0 · Letta/MemGPT · PydanticAI · AutoGPT · MetaGPT · MCP · smolagents

| Signal source | Keywords |
|---|---|
| Topics | `agent` · `multi-agent` · `langchain` · `llamaindex` · `autogen` · `crewai` · `rag` · `tool-use` · `memory` · `orchestration` · `mcp` · `function-calling` |
| Description | `agent` · `multi-agent` · `tool use` · `function calling` · `RAG` · `retrieval-augmented` · `memory` · `planning` · `orchestration` · `MCP` · `Model Context Protocol` |
| Deps | `langchain` · `langchain-core` · `llama-index` · `pyautogen` · `crewai` · `haystack-ai` · `mem0ai` · `pydantic-ai` |
| Filenames | `agent.py` · `tools.py` · `memory.py` · `mcp.json` · `.mcp/` |

---

### 21. Telemetry, Tracing & Observability

**Description:** Telemetry pipelines, distributed tracing, metrics, logging, ML experiment tracking, model monitoring, data lineage, and AI-specific evaluation/observability.

**Tech nodes:** OpenTelemetry · Prometheus · Grafana · Jaeger · Zipkin · MLflow · DVC · Weights & Biases · Evidently · Phoenix (Arize) · Netdata · Cilium/Hubble · LangSmith

| Signal source | Keywords |
|---|---|
| Topics | `opentelemetry` · `observability` · `tracing` · `metrics` · `logging` · `prometheus` · `grafana` · `mlflow` · `monitoring` · `telemetry` · `dvc` |
| Description | `telemetry` · `tracing` · `metrics` · `observability` · `distributed tracing` · `span` · `trace` · `MLflow` · `experiment tracking` · `data lineage` · `model monitoring` · `drift detection` |
| Deps | `opentelemetry-sdk` · `opentelemetry-api` · `mlflow` · `dvc` · `evidently` · `prometheus-client` · `wandb` · `arize-phoenix` |
| Filenames | `otel-config.yaml` · `prometheus.yml` · `grafana/` · `dvc.yaml` · `.dvc/` |

---

## Signal Weighting

Default weights apply to AI/ML and infrastructure domains. Hardware and systems domains use a different profile because repos in those areas rarely set GitHub topics — the primary signal type for software repos.

| Signal source | Default weight | Hardware domains weight |
|---|---|---|
| Topics | **0.40** | **0.15** — hardware repos rarely set topics |
| Description | **0.35** | **0.40** — description is more reliable |
| Deps | **0.15** | **0.10** — C/C++ deps hard to parse |
| Filenames | **0.10** | **0.35** — file extensions are the strongest signal |

**Hardware domains** (reduced topic weight): `os_kernel` · `drivers_firmware` · `fpga` · `eda_sim` · `interconnect` · `soc_riscv`

**Standard domains**: all others.

Domain assignment threshold: **0.15** weighted confidence (configurable in `config/ontology.yaml`).

---

## Cross-Domain Relationships

Key repos frequently span multiple domains. These are not conflicts — they are the most important repos to track because they sit at intersection points.

| Repo | Primary | Secondary |
|---|---|---|
| `llvm/circt` | `eda_sim` | `ai_compiler` · `fpga` · `soc_riscv` |
| `calyxir/calyx` | `eda_sim` | `ai_compiler` · `fpga` |
| `enjoy-digital/litepcie` | `interconnect` | `fpga` · `soc_riscv` |
| `spdk/spdk` | `interconnect` | `os_kernel` |
| `ucb-bar/chipyard` | `soc_riscv` | `fpga` · `eda_sim` |
| `iree-org/iree` | `ai_compiler` | `gpu_runtime` · `hw_abstraction` |
| `triton-lang/triton` | `ai_compiler` | `gpu_runtime` |
| `openxla/xla` | `ai_compiler` | `ml_training` · `gpu_runtime` |
| `verilator/verilator` | `eda_sim` | `soc_riscv` · `fpga` |
| `cocotb/cocotb` | `eda_sim` | `fpga` · `soc_riscv` |
| `mesa3d/mesa` | `drivers_firmware` | `gpu_runtime` |
| `ROCm/ROCm` | `gpu_runtime` | `drivers_firmware` · `ai_compiler` |
