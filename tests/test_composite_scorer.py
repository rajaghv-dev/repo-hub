"""Tests for composite_scorer.score."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from repo_hub.scorer.composite_scorer import score


@pytest.fixture
def base_profile() -> dict:
    return {
        "min_stars": 10,
        "domain_weights": {
            "ai_compiler": 2.8,
            "eda_sim": 3.0,
            "fpga": 3.0,
            "llm_inference": 2.0,
            "agentic": 0.0,  # hard exclude
        },
        "scoring_weights": {
            "activity": 0.20,
            "ontology": 0.30,
            "deps": 0.20,
            "profile": 0.30,
        },
        "tech_interests": ["mlir", "circt", "iree", "cocotb"],
        "priority_orgs": ["llvm", "openxla", "iree-org"],
        "preferred_languages": ["C++", "Python"],
    }


def test_fork_repo_excluded(base_profile, sample_domains):
    """Fork repo → score 0."""
    repo = {
        "id": "forker/circt",
        "org": "forker",
        "name": "circt",
        "is_fork": True,
        "is_archived": False,
        "stars": 100,
        "assigned_domains": ["ai_compiler"],
        "primary_domain": "ai_compiler",
        "matched_signals": {},
        "s_ontology": 0.8,
        "extracted_deps": {},
        "topics": [],
        "description": "",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 10,
        "language": "C++",
    }
    result = score(repo, base_profile, sample_domains, {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10})
    assert result["score"] == 0.0, "Fork repo should have score 0"


def test_low_star_repo_excluded(base_profile, sample_domains):
    """Repo with stars < min_stars → score 0."""
    repo = {
        "id": "tiny/project",
        "org": "tiny",
        "name": "project",
        "is_fork": False,
        "is_archived": False,
        "stars": 3,  # below min_stars=10
        "assigned_domains": ["ai_compiler"],
        "primary_domain": "ai_compiler",
        "matched_signals": {},
        "s_ontology": 0.5,
        "extracted_deps": {},
        "topics": [],
        "description": "",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 0,
        "language": "Python",
    }
    result = score(repo, base_profile, sample_domains, {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10})
    assert result["score"] == 0.0, "Low-star repo should have score 0"


def test_priority_org_gets_bonus(base_profile, sample_domains):
    """Repo from priority org → gets org_bonus in S_profile."""
    repo = {
        "id": "llvm/circt",
        "org": "llvm",  # in priority_orgs
        "name": "circt",
        "is_fork": False,
        "is_archived": False,
        "stars": 500,
        "assigned_domains": ["ai_compiler"],
        "primary_domain": "ai_compiler",
        "matched_signals": {},
        "s_ontology": 0.5,
        "extracted_deps": {},
        "topics": [],
        "description": "MLIR-based compiler",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 20,
        "language": "C++",
    }
    non_priority = dict(repo, id="unknown/circt", org="unknown")

    saturation = {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10}
    r1 = score(repo, base_profile, sample_domains, saturation)
    r2 = score(non_priority, base_profile, sample_domains, saturation)

    assert r1["s_profile"] > r2["s_profile"], "Priority org should get higher S_profile"


def test_tech_interest_match_gets_bonus(base_profile, sample_domains):
    """Tech interest match → gets tech_bonus."""
    repo_with_tech = {
        "id": "org/circt-tool",
        "org": "org",
        "name": "circt-tool",
        "is_fork": False,
        "is_archived": False,
        "stars": 100,
        "assigned_domains": ["ai_compiler"],
        "primary_domain": "ai_compiler",
        "matched_signals": {"ai_compiler": ["mlir (topic)", "MLIR (desc)"]},
        "s_ontology": 0.5,
        "extracted_deps": {},
        "topics": ["mlir"],  # in tech_interests
        "description": "Uses MLIR",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 5,
        "language": "C++",
    }
    repo_without_tech = dict(repo_with_tech, topics=[], matched_signals={})

    saturation = {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10}
    r1 = score(repo_with_tech, base_profile, sample_domains, saturation)
    r2 = score(repo_without_tech, base_profile, sample_domains, saturation)

    assert r1["s_profile"] > r2["s_profile"], "Tech interest match should get higher S_profile"


def test_zero_weight_domain_excluded(base_profile, sample_domains):
    """Repo with all assigned domains having weight 0 → excluded."""
    repo = {
        "id": "langchain-ai/langchain",
        "org": "langchain-ai",
        "name": "langchain",
        "is_fork": False,
        "is_archived": False,
        "stars": 5000,
        "assigned_domains": ["agentic"],  # weight 0 in profile
        "primary_domain": "agentic",
        "matched_signals": {},
        "s_ontology": 0.7,
        "extracted_deps": {},
        "topics": ["agent"],
        "description": "LangChain agentic system",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 30,
        "language": "Python",
    }
    result = score(repo, base_profile, sample_domains, {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10})
    assert result["score"] == 0.0, "Zero-weight domain repo should be excluded"


def test_final_score_in_range(base_profile, sample_domains):
    """Final score should be in [0, 100]."""
    repo = {
        "id": "great/project",
        "org": "openxla",
        "name": "project",
        "is_fork": False,
        "is_archived": False,
        "stars": 5000,
        "assigned_domains": ["ai_compiler", "gpu_runtime"],
        "primary_domain": "ai_compiler",
        "matched_signals": {"ai_compiler": ["mlir (topic)"]},
        "s_ontology": 0.9,
        "extracted_deps": {"requirements.txt": ["triton", "torch"]},
        "topics": ["mlir", "cuda", "compiler"],
        "description": "AI compiler using MLIR",
        "last_pushed_at": datetime.now(timezone.utc),
        "open_issues": 40,
        "language": "C++",
    }
    result = score(repo, base_profile, sample_domains, {"hardware": 3, "compute": 6, "aiml": 12, "infra": 10})
    assert 0.0 <= result["score"] <= 100.0, f"Score out of range: {result['score']}"
