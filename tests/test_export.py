"""Tests for export functions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _sample_repos() -> list[dict]:
    return [
        {
            "id": "llvm/circt",
            "org": "llvm",
            "name": "circt",
            "url": "https://github.com/llvm/circt",
            "description": "MLIR-based hardware compiler",
            "stars": 2500,
            "forks": 300,
            "open_issues": 45,
            "language": "C++",
            "license": "Apache-2.0",
            "last_pushed_at": datetime(2026, 4, 25, tzinfo=timezone.utc),
            "is_archived": False,
            "is_fork": False,
            "topics": ["mlir", "compiler"],
            "assigned_domains": ["ai_compiler", "eda_sim"],
            "extracted_deps": {"requirements.txt": ["cocotb"]},
            "s_activity": 0.85,
            "s_ontology": 0.76,
            "s_deps": 0.67,
            "s_profile": 0.95,
            "score": 82.5,
            "matched_signals": {"ai_compiler": ["mlir (topic)"]},
            "source": "github",
            "classified_at": datetime.now(timezone.utc),
            "fetched_at": datetime.now(timezone.utc),
            "primary_domain": "ai_compiler",
        },
        {
            "id": "vllm-project/vllm",
            "org": "vllm-project",
            "name": "vllm",
            "url": "https://github.com/vllm-project/vllm",
            "description": "LLM inference engine",
            "stars": 20000,
            "forks": 2000,
            "open_issues": 200,
            "language": "Python",
            "license": "Apache-2.0",
            "last_pushed_at": datetime(2026, 4, 26, tzinfo=timezone.utc),
            "is_archived": False,
            "is_fork": False,
            "topics": ["llm", "inference"],
            "assigned_domains": ["llm_inference"],
            "extracted_deps": {},
            "s_activity": 0.90,
            "s_ontology": 0.85,
            "s_deps": 0.50,
            "s_profile": 0.70,
            "score": 75.0,
            "matched_signals": {},
            "source": "github",
            "classified_at": datetime.now(timezone.utc),
            "fetched_at": datetime.now(timezone.utc),
            "primary_domain": "llm_inference",
        },
    ]


def test_to_parquet_writes_valid_file(tmp_path):
    """to_parquet writes a valid Parquet file."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        pytest.skip("pyarrow not available")

    from repo_hub.renderer.export import to_parquet

    repos = _sample_repos()
    output = tmp_path / "repos.parquet"
    to_parquet(repos, output)

    assert output.exists(), "Parquet file should exist"
    assert output.stat().st_size > 0, "Parquet file should not be empty"

    # Read back and verify
    table = pq.read_table(str(output))
    assert table.num_rows == 2
    assert "id" in table.column_names


def test_to_parquet_empty(tmp_path):
    """to_parquet handles empty repos list."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        pytest.skip("pyarrow not available")

    from repo_hub.renderer.export import to_parquet

    output = tmp_path / "empty.parquet"
    to_parquet([], output)
    assert output.exists()


def test_to_csv_writes_file(tmp_path):
    """to_csv writes a CSV with correct headers."""
    from repo_hub.renderer.export import to_csv

    repos = _sample_repos()
    output = tmp_path / "repos.csv"
    to_csv(repos, output)

    assert output.exists()
    content = output.read_text()
    assert "id" in content
    assert "llvm/circt" in content


def test_to_json_summary(tmp_path):
    """to_json_summary creates valid JSON with expected keys."""
    from repo_hub.renderer.export import to_json_summary

    repos = _sample_repos()
    output = tmp_path / "summary.json"
    to_json_summary(repos, output)

    assert output.exists()
    data = json.loads(output.read_text())
    assert "generated_at" in data
    assert "total_repos" in data
    assert data["total_repos"] == 2
    assert "domain_counts" in data
    assert "ai_compiler" in data["domain_counts"]


def test_generate_report_creates_markdown(tmp_path):
    """generate_report creates REPORT.md with expected sections."""
    from repo_hub.renderer.export import generate_report

    repos = _sample_repos()
    stats = {
        "total": 2,
        "by_domain": [
            {"domain": "ai_compiler", "cnt": 1, "avg_score": 82.5, "top_score": 82.5},
            {"domain": "llm_inference", "cnt": 1, "avg_score": 75.0, "top_score": 75.0},
        ],
        "top_orgs": [],
    }

    output = tmp_path / "REPORT.md"
    generate_report(repos, stats, output)

    assert output.exists()
    content = output.read_text()

    # Check for expected sections
    assert "# repo-hub Report" in content
    assert "## Summary" in content
    assert "## Top Repos by Domain" in content
    assert "## Domain Statistics" in content
    assert "llvm/circt" in content or "circt" in content
