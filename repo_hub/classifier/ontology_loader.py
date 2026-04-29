"""Parse ontology.yaml into typed domain objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DomainSignals:
    topics: list[str]
    description: list[str]
    deps: list[str]
    filenames: list[str]


@dataclass
class Domain:
    id: str
    label: str
    group: str  # hardware|compute|aiml|infra
    saturation_group: str
    signals: DomainSignals
    weight_profile: str  # "hardware" or "standard"


def load_ontology(path: Path) -> tuple[list[Domain], dict]:
    """
    Load and parse ontology.yaml.

    Returns:
        (domains, config) where config has threshold, signal_weights,
        saturation values.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    hardware_domain_ids = set(raw.get("hardware_domains", []))
    signal_weights = raw.get("signal_weights", {})
    saturation = raw.get("saturation", {})
    threshold = raw.get("threshold", 0.15)

    domains: list[Domain] = []
    for d in raw.get("domains", []):
        signals_raw = d.get("signals", {})
        signals = DomainSignals(
            topics=[str(t) for t in signals_raw.get("topics", [])],
            description=[str(t) for t in signals_raw.get("description", [])],
            deps=[str(t) for t in signals_raw.get("deps", [])],
            filenames=[str(t) for t in signals_raw.get("filenames", [])],
        )

        domain_id = d["id"]
        weight_profile = (
            "hardware" if domain_id in hardware_domain_ids else "standard"
        )

        domain = Domain(
            id=domain_id,
            label=d.get("label", domain_id),
            group=d.get("group", "infra"),
            saturation_group=d.get("saturation_group", "infra"),
            signals=signals,
            weight_profile=weight_profile,
        )
        domains.append(domain)

    config = {
        "threshold": threshold,
        "signal_weights": signal_weights,
        "saturation": saturation,
        "hardware_domains": hardware_domain_ids,
    }

    return domains, config
