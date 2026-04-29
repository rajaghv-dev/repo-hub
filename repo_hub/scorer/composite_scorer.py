"""Composite score computation combining all sub-scores."""
from __future__ import annotations

from repo_hub.classifier.ontology_loader import Domain
from repo_hub.scorer.activity_scorer import score_activity
from repo_hub.scorer.relevance_scorer import score_deps


def score(
    repo: dict,
    profile: dict,
    domains: list[Domain],
    saturation_config: dict,
) -> dict:
    """
    Compute the full composite score for a repo.

    Returns the repo dict with s_activity, s_ontology, s_deps, s_profile, score added.
    Hard filters return score=0.
    """
    repo = dict(repo)

    # ── Hard filters ─────────────────────────────────────────────────────────
    min_stars = profile.get("min_stars", 10)
    if repo.get("stars", 0) < min_stars:
        repo["score"] = 0.0
        return repo

    if repo.get("is_fork", False):
        repo["score"] = 0.0
        return repo

    assigned_domains = repo.get("assigned_domains", []) or []

    # If all assigned domain weights are 0, exclude
    domain_weights = profile.get("domain_weights", {})
    if assigned_domains:
        all_zero = all(domain_weights.get(d, 1.0) == 0.0 for d in assigned_domains)
        if all_zero:
            repo["score"] = 0.0
            return repo

    # ── Sub-scores ────────────────────────────────────────────────────────────

    # S_activity
    s_activity = score_activity(repo)
    repo["s_activity"] = s_activity

    # S_ontology (already computed during classification)
    s_ontology = repo.get("s_ontology", 0.0)

    # S_deps
    s_deps_val = score_deps(repo, domains, saturation_config)
    repo["s_deps"] = s_deps_val

    # S_profile
    s_profile = _score_profile(repo, profile, domains)
    repo["s_profile"] = s_profile

    # ── Composite ────────────────────────────────────────────────────────────
    scoring_weights = profile.get("scoring_weights", {})
    w_activity = scoring_weights.get("activity", 0.20)
    w_ontology = scoring_weights.get("ontology", 0.30)
    w_deps = scoring_weights.get("deps", 0.20)
    w_profile = scoring_weights.get("profile", 0.30)

    final = (
        w_activity * s_activity
        + w_ontology * s_ontology
        + w_deps * s_deps_val
        + w_profile * s_profile
    )
    repo["score"] = round(final * 100, 1)
    return repo


def _score_profile(
    repo: dict,
    profile: dict,
    domains: list[Domain],
) -> float:
    """Compute S_profile in [0, 1]."""
    domain_weights = profile.get("domain_weights", {})
    tech_interests = set(t.lower() for t in profile.get("tech_interests", []))
    priority_orgs = set(o.lower() for o in profile.get("priority_orgs", []))
    preferred_languages = set(profile.get("preferred_languages", []))

    assigned_domains = repo.get("assigned_domains", []) or []

    if not assigned_domains:
        return 0.0

    # Best domain weight
    best_weight = max(domain_weights.get(d, 1.0) for d in assigned_domains)
    norm_weight = min(1.0, best_weight / 3.0)

    # Tech bonus: check if any matched signal or topic is in tech_interests
    tech_bonus = 0.0
    matched_signals = repo.get("matched_signals", {}) or {}
    repo_topics = {t.lower() for t in (repo.get("topics") or [])}

    # Check topics
    if repo_topics.intersection(tech_interests):
        tech_bonus = 0.20
    else:
        # Check all signal strings
        for signals_list in matched_signals.values():
            for signal_str in signals_list:
                # Extract the signal keyword (before the " (topic)" etc.)
                kw = signal_str.split(" (")[0].lower()
                if kw in tech_interests:
                    tech_bonus = 0.20
                    break
            if tech_bonus:
                break

    # Org bonus
    org_bonus = 0.10 if (repo.get("org", "").lower() in priority_orgs) else 0.0

    # Language bonus
    lang = repo.get("language") or ""
    lang_bonus = 0.05 if lang in preferred_languages else 0.0

    s_profile = min(1.0, norm_weight + tech_bonus + org_bonus + lang_bonus)
    return round(s_profile, 6)


def score_batch(
    repos: list[dict],
    profile: dict,
    domains: list[Domain],
    saturation_config: dict,
) -> list[dict]:
    """Score a batch of repos."""
    return [score(repo, profile, domains, saturation_config) for repo in repos]
