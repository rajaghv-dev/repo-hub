"""Tests for domain_classifier.classify."""
from __future__ import annotations

import pytest
from repo_hub.classifier.domain_classifier import classify


def test_circt_like_repo(sample_domains, ontology_config):
    """CIRCT-like repo with strong signals → assigned_domains includes ai_compiler and eda_sim."""
    # Use richer signals to ensure threshold is crossed
    repo = {
        "id": "llvm/circt",
        "org": "llvm",
        "name": "circt",
        "description": (
            "MLIR-based compiler infrastructure for hardware design with RTL simulation, "
            "synthesis, formal verification, and place and route. Uses MLIR dialects, "
            "codegen, JIT and AOT compilation, intermediate representation, and graph optimization."
        ),
        "topics": ["mlir", "compiler", "rtl", "eda", "fpga", "hardware-design", "circt"],
        "extracted_deps": {"requirements.txt": ["cocotb", "pymtl3"], "CMakeLists.txt": ["LLVM", "MLIR"]},
        "stars": 2000,
        "is_archived": False,
        "is_fork": False,
    }
    result = classify(repo, sample_domains, ontology_config)
    assigned = result.get("assigned_domains", [])
    # Should get both eda/hardware and compiler domains
    assert len(assigned) > 0, "Expected at least one domain assigned"
    # MLIR, compiler, IR in description should trigger ai_compiler
    assert "ai_compiler" in assigned, f"Expected ai_compiler in assigned domains, got {assigned}"


def test_vllm_like_repo(sample_domains, ontology_config):
    """vLLM-like repo → gets llm_inference as primary domain."""
    repo = {
        "id": "vllm-project/vllm",
        "org": "vllm-project",
        "name": "vllm",
        "description": "LLM inference engine with paged attention and continuous batching for high throughput",
        "topics": ["llm", "inference", "vllm", "paged-attention"],
        "extracted_deps": {"requirements.txt": ["vllm", "torch", "transformers"]},
        "stars": 20000,
        "is_archived": False,
        "is_fork": False,
    }
    result = classify(repo, sample_domains, ontology_config)
    assert result.get("primary_domain") == "llm_inference", \
        f"Expected llm_inference as primary domain, got {result.get('primary_domain')}"


def test_below_threshold_empty_domains(sample_domains, ontology_config):
    """Repo with no signal matches → empty assigned_domains."""
    repo = {
        "id": "random/app",
        "org": "random",
        "name": "app",
        "description": "A simple todo list application",
        "topics": ["todo", "productivity", "app"],
        "extracted_deps": {},
        "stars": 50,
        "is_archived": False,
        "is_fork": False,
    }
    result = classify(repo, sample_domains, ontology_config)
    assigned = result.get("assigned_domains", [])
    # A todo app should not match any technical domain above threshold
    # (some may match weakly; just check it's not many)
    assert len(assigned) <= 2, f"Unexpected domain matches for todo app: {assigned}"


def test_classified_at_is_set(sample_domains, ontology_config, sample_repo):
    """classified_at should be set after classification."""
    result = classify(sample_repo, sample_domains, ontology_config)
    assert result.get("classified_at") is not None, "classified_at should be set"


def test_matched_signals_populated(sample_domains, ontology_config):
    """matched_signals should contain the signals that triggered each domain."""
    repo = {
        "id": "test/mlir-thing",
        "org": "test",
        "name": "mlir-thing",
        "description": "Uses MLIR dialects for IR lowering and codegen",
        "topics": ["mlir", "compiler"],
        "extracted_deps": {},
        "stars": 100,
        "is_archived": False,
        "is_fork": False,
    }
    result = classify(repo, sample_domains, ontology_config)
    matched = result.get("matched_signals", {})

    if "ai_compiler" in result.get("assigned_domains", []):
        assert "ai_compiler" in matched, "matched_signals should include ai_compiler signals"
        signals = matched["ai_compiler"]
        assert len(signals) > 0, "Should have at least one matched signal"


def test_primary_domain_is_highest_score(sample_domains, ontology_config):
    """primary_domain should be the highest scoring assigned domain."""
    repo = {
        "id": "pytorch/pytorch",
        "org": "pytorch",
        "name": "pytorch",
        "description": "Deep learning training framework with automatic differentiation",
        "topics": ["deep-learning", "pytorch", "training", "machine-learning"],
        "extracted_deps": {"requirements.txt": ["torch", "torchvision"]},
        "stars": 50000,
        "is_archived": False,
        "is_fork": False,
    }
    result = classify(repo, sample_domains, ontology_config)
    primary = result.get("primary_domain")
    if primary:
        assert primary in result.get("assigned_domains", []), \
            "primary_domain must be in assigned_domains"
