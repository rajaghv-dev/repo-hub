"""Shared test fixtures."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def sample_repo() -> dict:
    """A minimal repo dict matching the repos schema."""
    return {
        "id": "llvm/circt",
        "org": "llvm",
        "name": "circt",
        "url": "https://github.com/llvm/circt",
        "description": "MLIR-based compiler for hardware design and RTL generation",
        "stars": 2500,
        "forks": 300,
        "open_issues": 45,
        "language": "C++",
        "license": "Apache-2.0",
        "last_pushed_at": datetime(2026, 4, 25, tzinfo=timezone.utc),
        "is_archived": False,
        "is_fork": False,
        "topics": ["mlir", "compiler", "rtl", "eda", "fpga", "hardware-design"],
        "assigned_domains": [],
        "extracted_deps": {},
        "s_activity": 0.0,
        "s_ontology": 0.0,
        "s_deps": 0.0,
        "s_profile": 0.0,
        "score": 0.0,
        "matched_signals": {},
        "source": "github",
        "classified_at": None,
        "fetched_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_domains():
    """Load domains from the real config/ontology.yaml."""
    from repo_hub.classifier.ontology_loader import load_ontology

    # Walk up to find config/ontology.yaml
    here = Path(__file__).parent
    for candidate in [here.parent / "config" / "ontology.yaml"]:
        if candidate.exists():
            domains, config = load_ontology(candidate)
            return domains

    pytest.skip("config/ontology.yaml not found")


@pytest.fixture
def ontology_config():
    """Load full ontology config."""
    from repo_hub.classifier.ontology_loader import load_ontology

    here = Path(__file__).parent
    path = here.parent / "config" / "ontology.yaml"
    if not path.exists():
        pytest.skip("config/ontology.yaml not found")
    _, config = load_ontology(path)
    return config


@pytest.fixture
def sample_profile() -> dict:
    """Load profile from config/profile.yaml."""
    here = Path(__file__).parent
    path = here.parent / "config" / "profile.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    # Fallback minimal profile
    return {
        "domain_weights": {
            "ai_compiler": 2.8,
            "eda_sim": 3.0,
            "fpga": 3.0,
            "llm_inference": 2.0,
            "agentic": 0.5,
        },
        "scoring_weights": {
            "activity": 0.20,
            "ontology": 0.30,
            "deps": 0.20,
            "profile": 0.30,
        },
        "tech_interests": ["mlir", "circt", "iree", "verilator", "cocotb"],
        "priority_orgs": ["llvm", "openxla", "iree-org", "YosysHQ"],
        "preferred_languages": ["C++", "Python", "Rust"],
    }


@pytest.fixture
def mock_github_response() -> list[dict]:
    """A list of fake GitHub API repo responses."""
    return [
        {
            "name": "test-repo",
            "html_url": "https://github.com/testorg/test-repo",
            "description": "A test repository for unit tests",
            "stargazers_count": 100,
            "forks_count": 10,
            "open_issues_count": 5,
            "language": "Python",
            "license": {"spdx_id": "MIT"},
            "pushed_at": "2026-04-01T00:00:00Z",
            "archived": False,
            "fork": False,
            "topics": ["testing", "python"],
        }
    ]


@pytest.fixture
def tmp_cache(tmp_path):
    """An in-memory (temp dir) Cache instance."""
    from repo_hub.storage.cache import Cache
    return Cache(tmp_path, ttl_hours=24)
