"""Keyword-based domain matching for repos."""
from __future__ import annotations

import fnmatch
import re
from typing import Any

from repo_hub.classifier.ontology_loader import Domain


def _topic_match(repo_topics: list[str], signal_topics: list[str]) -> tuple[int, int]:
    """Count how many signal topics appear in the repo's topic list."""
    repo_set = {t.lower() for t in repo_topics}
    matched = sum(1 for t in signal_topics if t.lower() in repo_set)
    return matched, len(signal_topics)


def _description_match(
    description: str, signal_keywords: list[str]
) -> tuple[int, int]:
    """Count how many signal keywords appear in the repo description (case-insensitive)."""
    if not description:
        return 0, len(signal_keywords)
    desc_lower = description.lower()
    matched = 0
    for kw in signal_keywords:
        if kw.lower() in desc_lower:
            matched += 1
    return matched, len(signal_keywords)


def _deps_match(
    extracted_deps: dict[str, list[str]], signal_deps: list[str]
) -> tuple[int, int]:
    """Count how many signal deps appear across all extracted dep files."""
    if not extracted_deps:
        return 0, len(signal_deps)

    # Build flat set of all extracted dep names (lower case)
    all_deps: set[str] = set()
    for dep_list in extracted_deps.values():
        for dep in dep_list:
            all_deps.add(dep.lower())

    signal_set = {d.lower() for d in signal_deps}
    matched = len(all_deps.intersection(signal_set))
    return matched, len(signal_deps)


def _filename_match(
    extracted_deps: dict[str, list[str]],
    filenames_in_repo: list[str],
    signal_filenames: list[str],
) -> tuple[int, int]:
    """
    Count how many signal filename patterns are matched.

    Uses glob-style matching against:
    - Keys of extracted_deps (the dep files themselves)
    - Any filenames passed in filenames_in_repo
    """
    candidates = list(extracted_deps.keys()) + list(filenames_in_repo)
    if not candidates:
        return 0, len(signal_filenames)

    matched = 0
    for pattern in signal_filenames:
        for candidate in candidates:
            # fnmatch handles glob patterns like *.sv, *.bpf.c
            if fnmatch.fnmatch(candidate, pattern) or fnmatch.fnmatch(
                candidate.lower(), pattern.lower()
            ):
                matched += 1
                break
            # Also match basename
            basename = candidate.split("/")[-1]
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(
                basename.lower(), pattern.lower()
            ):
                matched += 1
                break

    return matched, len(signal_filenames)


def match_repo(
    repo: dict,
    domains: list[Domain],
    weights_config: dict,
) -> dict[str, float]:
    """
    Compute domain scores for a repo.

    Returns {domain_id: score} for all domains. Score is in [0.0, 1.0].
    """
    signal_weights = weights_config.get("signal_weights", {})
    standard_weights = signal_weights.get(
        "standard", {"topics": 0.40, "description": 0.35, "deps": 0.15, "filenames": 0.10}
    )
    hardware_weights = signal_weights.get(
        "hardware", {"topics": 0.15, "description": 0.40, "deps": 0.10, "filenames": 0.35}
    )

    repo_topics = repo.get("topics", []) or []
    description = repo.get("description", "") or ""
    extracted_deps = repo.get("extracted_deps", {}) or {}
    # We don't have a separate filenames list; use dep file keys for filename matching
    filenames_in_repo: list[str] = []

    scores: dict[str, float] = {}

    for domain in domains:
        weights = (
            hardware_weights if domain.weight_profile == "hardware" else standard_weights
        )

        # Topics signal
        t_matched, t_total = _topic_match(repo_topics, domain.signals.topics)
        topic_conf = t_matched / t_total if t_total > 0 else 0.0

        # Description signal
        d_matched, d_total = _description_match(description, domain.signals.description)
        desc_conf = d_matched / d_total if d_total > 0 else 0.0

        # Deps signal
        dep_matched, dep_total = _deps_match(extracted_deps, domain.signals.deps)
        dep_conf = dep_matched / dep_total if dep_total > 0 else 0.0

        # Filenames signal
        f_matched, f_total = _filename_match(
            extracted_deps, filenames_in_repo, domain.signals.filenames
        )
        file_conf = f_matched / f_total if f_total > 0 else 0.0

        domain_score = (
            weights["topics"] * topic_conf
            + weights["description"] * desc_conf
            + weights["deps"] * dep_conf
            + weights["filenames"] * file_conf
        )
        scores[domain.id] = round(domain_score, 6)

    return scores
