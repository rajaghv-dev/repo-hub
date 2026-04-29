"""Dependency-match sub-score computation."""
from __future__ import annotations

from repo_hub.classifier.ontology_loader import Domain


def score_deps(
    repo: dict,
    domains: list[Domain],
    saturation_config: dict,
) -> float:
    """
    Compute S_deps in [0, 1].

    Counts dep hits: extracted_deps values that appear in any domain's signals.deps.
    Determines saturation from the primary domain's saturation_group.
    """
    extracted_deps: dict[str, list[str]] = repo.get("extracted_deps") or {}
    if not extracted_deps:
        return 0.0

    # Build flat set of all extracted deps (lower case)
    all_deps: set[str] = set()
    for dep_list in extracted_deps.values():
        for dep in dep_list:
            all_deps.add(dep.lower())

    if not all_deps:
        return 0.0

    # Build reference set of all domain signal deps
    all_signal_deps: set[str] = set()
    for domain in domains:
        for dep in domain.signals.deps:
            all_signal_deps.add(dep.lower())

    # Count hits
    dep_hits = len(all_deps.intersection(all_signal_deps))

    if dep_hits == 0:
        return 0.0

    # Determine saturation from primary domain's saturation group
    primary_domain = repo.get("primary_domain")
    saturation_group = "infra"  # default

    if primary_domain:
        for domain in domains:
            if domain.id == primary_domain:
                saturation_group = domain.saturation_group
                break

    # Map saturation_group to numeric saturation value
    # saturation_config maps group names like "hardware", "compute", "aiml", "infra"
    saturation = saturation_config.get(saturation_group, 10)

    s_deps = min(1.0, dep_hits / saturation)
    return round(s_deps, 6)
