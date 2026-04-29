"""Tests for keyword_matcher.match_repo."""
from __future__ import annotations

import pytest
from repo_hub.classifier.keyword_matcher import match_repo


def test_fpga_topic_match(sample_domains, ontology_config):
    """Repo with 'fpga' topic → gets fpga domain score > 0."""
    repo = {
        "topics": ["fpga", "verilog"],
        "description": "FPGA design toolkit",
        "extracted_deps": {},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    assert scores.get("fpga", 0) > 0, "Expected fpga score > 0 for repo with fpga topic"


def test_mlir_description_match(sample_domains, ontology_config):
    """Repo with 'MLIR' in description → gets ai_compiler domain score > 0."""
    repo = {
        "topics": [],
        "description": "A compiler using MLIR dialects and IR transformations",
        "extracted_deps": {},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    assert scores.get("ai_compiler", 0) > 0, "Expected ai_compiler score > 0 for MLIR description"


def test_cocotb_dep_match(sample_domains, ontology_config):
    """Repo with 'cocotb' dep → gets eda_sim domain score > 0."""
    repo = {
        "topics": [],
        "description": "Hardware simulation library",
        "extracted_deps": {"requirements.txt": ["cocotb", "pytest"]},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    assert scores.get("eda_sim", 0) > 0, "Expected eda_sim score > 0 for cocotb dep"


def test_sv_file_match(sample_domains, ontology_config):
    """Repo with '*.sv' files → gets hardware domain scores."""
    repo = {
        "topics": [],
        "description": "SystemVerilog design",
        "extracted_deps": {"top.sv": []},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    # .sv files should match fpga or eda_sim
    hw_score = max(scores.get("fpga", 0), scores.get("eda_sim", 0))
    assert hw_score > 0, "Expected hardware score > 0 for .sv file"


def test_no_matches_below_threshold(sample_domains, ontology_config):
    """Repo with no matches → all scores near 0."""
    repo = {
        "topics": ["cooking", "recipes"],
        "description": "A recipe management application",
        "extracted_deps": {"requirements.txt": ["flask", "jinja2"]},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    threshold = ontology_config.get("threshold", 0.15)
    above_threshold = [d for d, s in scores.items() if s >= threshold]
    assert len(above_threshold) == 0, f"Expected no domain above threshold but got {above_threshold}"


def test_hardware_weight_profile(sample_domains, ontology_config):
    """Hardware repos use hardware weight profile (lower topics weight)."""
    # Find a hardware domain
    hw_domain = None
    for d in sample_domains:
        if d.weight_profile == "hardware":
            hw_domain = d
            break
    assert hw_domain is not None, "No hardware domain found"
    assert hw_domain.weight_profile == "hardware"

    # Verify score calculation uses hardware weights
    # Hardware domains should weight filenames more than topics
    signal_weights = ontology_config.get("signal_weights", {})
    hw_weights = signal_weights.get("hardware", {})
    std_weights = signal_weights.get("standard", {})
    assert hw_weights.get("topics", 0.4) < std_weights.get("topics", 0.4), \
        "Hardware profile should have lower topics weight"
    assert hw_weights.get("filenames", 0.1) > std_weights.get("filenames", 0.1), \
        "Hardware profile should have higher filenames weight"


def test_scores_in_range(sample_domains, ontology_config):
    """All domain scores should be in [0, 1] range."""
    repo = {
        "topics": ["cuda", "deep-learning", "gpu"],
        "description": "CUDA kernel optimization library",
        "extracted_deps": {"requirements.txt": ["cupy", "torch"]},
    }
    scores = match_repo(repo, sample_domains, ontology_config)
    for domain_id, score in scores.items():
        assert 0.0 <= score <= 1.0, f"Score for {domain_id} out of range: {score}"
