"""Domain classification using keyword matching."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from repo_hub.classifier.keyword_matcher import match_repo
from repo_hub.classifier.ontology_loader import Domain


def classify(
    repo: dict,
    domains: list[Domain],
    weights_config: dict,
    threshold: float = 0.15,
) -> dict:
    """
    Classify a repo against the ontology.

    Returns an updated repo dict with:
    - assigned_domains: list of domain IDs that scored >= threshold
    - primary_domain: highest-scoring domain
    - matched_signals: {domain_id: [signal_string, ...]}
    - s_ontology: max domain score (0.0-1.0)
    - classified_at: timestamp
    """
    repo = dict(repo)  # shallow copy

    scores = match_repo(repo, domains, weights_config)

    # Determine which domains pass threshold
    assigned = {d_id: score for d_id, score in scores.items() if score >= threshold}
    primary_domain = max(assigned, key=assigned.get) if assigned else None

    # Build matched_signals: for each assigned domain, list the signals that matched
    matched_signals: dict[str, list[str]] = {}
    for domain in domains:
        if domain.id not in assigned:
            continue

        signals: list[str] = []
        repo_topics = {t.lower() for t in (repo.get("topics") or [])}
        description = (repo.get("description") or "").lower()
        extracted_deps: dict[str, list[str]] = repo.get("extracted_deps") or {}

        for t in domain.signals.topics:
            if t.lower() in repo_topics:
                signals.append(f"{t} (topic)")

        for kw in domain.signals.description:
            if kw.lower() in description:
                signals.append(f"{kw} (desc)")

        all_deps = set()
        for dep_list in extracted_deps.values():
            all_deps.update(d.lower() for d in dep_list)
        for dep in domain.signals.deps:
            if dep.lower() in all_deps:
                signals.append(f"{dep} (dep)")

        dep_keys = list(extracted_deps.keys())
        import fnmatch
        for pattern in domain.signals.filenames:
            for key in dep_keys:
                if fnmatch.fnmatch(key, pattern) or fnmatch.fnmatch(key.lower(), pattern.lower()):
                    signals.append(f"{pattern} (file)")
                    break

        if signals:
            matched_signals[domain.id] = signals

    repo["assigned_domains"] = list(assigned.keys())
    repo["primary_domain"] = primary_domain
    repo["matched_signals"] = matched_signals
    repo["s_ontology"] = max(assigned.values()) if assigned else 0.0
    repo["classified_at"] = datetime.now(timezone.utc)

    return repo


def classify_batch(
    repos: list[dict],
    domains: list[Domain],
    weights_config: dict,
    threshold: float = 0.15,
) -> list[dict]:
    """Classify a batch of repos."""
    return [classify(repo, domains, weights_config, threshold) for repo in repos]
