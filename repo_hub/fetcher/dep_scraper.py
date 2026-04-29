"""Fetch and parse dependency files from GitHub repositories."""
from __future__ import annotations

import re
from typing import Any

from repo_hub.fetcher.github_client import GitHubClient
from repo_hub.storage.cache import Cache

DEP_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "CMakeLists.txt",
    "package.json",
    "Cargo.toml",
    "go.mod",
]


def parse_requirements_txt(content: str) -> list[str]:
    """Parse requirements.txt format. Handles comments, version specs, extras."""
    deps = []
    if not content:
        return deps
    try:
        for line in content.splitlines():
            line = line.strip()
            # Skip comments, empty lines, options (-r, -i, --index-url, etc.)
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Strip inline comments
            if " #" in line:
                line = line[: line.index(" #")].strip()
            # Strip extras: package[extra1,extra2]
            line = re.sub(r"\[.*?\]", "", line)
            # Strip version specifiers
            name = re.split(r"[><=!;@~\s]", line)[0].strip()
            if name:
                deps.append(name.lower())
    except Exception:
        pass
    return deps


def parse_pyproject_toml(content: str) -> list[str]:
    """Parse pyproject.toml for dependencies (PEP 621 and Poetry formats)."""
    deps = []
    if not content:
        return deps
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            # Fallback: regex-based extraction
            return _parse_pyproject_toml_regex(content)

    try:
        data = tomllib.loads(content)
        # PEP 621: [project].dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        for dep in project_deps:
            name = re.split(r"[><=!;@~\s\[]", str(dep))[0].strip().lower()
            if name:
                deps.append(name)

        # Poetry: [tool.poetry.dependencies]
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for name in poetry_deps:
            if name.lower() != "python":
                deps.append(name.lower())

        # Optional deps: [project.optional-dependencies]
        opt_deps = data.get("project", {}).get("optional-dependencies", {})
        for group_deps in opt_deps.values():
            for dep in group_deps:
                name = re.split(r"[><=!;@~\s\[]", str(dep))[0].strip().lower()
                if name:
                    deps.append(name)
    except Exception:
        deps = _parse_pyproject_toml_regex(content)

    return list(dict.fromkeys(deps))  # deduplicate preserving order


def _parse_pyproject_toml_regex(content: str) -> list[str]:
    """Regex fallback for pyproject.toml parsing."""
    deps = []
    try:
        # Match strings in dependencies arrays
        in_deps_section = False
        for line in content.splitlines():
            stripped = line.strip()
            if re.match(r"\[(?:project|tool\.poetry)\.(?:optional-)?dependencies", stripped):
                in_deps_section = True
                continue
            if stripped.startswith("[") and not stripped.startswith("[project.optional"):
                in_deps_section = False
            if in_deps_section:
                m = re.search(r'"([a-zA-Z0-9_\-\.]+)', stripped)
                if m:
                    deps.append(m.group(1).lower())
    except Exception:
        pass
    return deps


def parse_cmake(content: str) -> list[str]:
    """Extract find_package() and FetchContent_Declare() names from CMakeLists.txt."""
    deps = []
    if not content:
        return deps
    try:
        # find_package(PackageName ...)
        for m in re.finditer(r"find_package\s*\(\s*([A-Za-z0-9_]+)", content, re.IGNORECASE):
            deps.append(m.group(1))

        # FetchContent_Declare(name ...)
        for m in re.finditer(r"FetchContent_Declare\s*\(\s*([A-Za-z0-9_]+)", content, re.IGNORECASE):
            deps.append(m.group(1))
    except Exception:
        pass
    return list(dict.fromkeys(deps))


def parse_package_json(content: str) -> list[str]:
    """Parse package.json dependencies and devDependencies."""
    deps = []
    if not content:
        return deps
    try:
        import json
        data = json.loads(content)
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            for name in data.get(key, {}):
                deps.append(name.lower())
    except Exception:
        pass
    return list(dict.fromkeys(deps))


def parse_cargo_toml(content: str) -> list[str]:
    """Parse Cargo.toml [dependencies] section."""
    deps = []
    if not content:
        return deps
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return _parse_cargo_toml_regex(content)

    try:
        data = tomllib.loads(content)
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            for name in data.get(section, {}):
                deps.append(name.lower())
        # Also workspace dependencies
        for name in data.get("workspace", {}).get("dependencies", {}):
            deps.append(name.lower())
    except Exception:
        deps = _parse_cargo_toml_regex(content)

    return list(dict.fromkeys(deps))


def _parse_cargo_toml_regex(content: str) -> list[str]:
    """Regex fallback for Cargo.toml."""
    deps = []
    try:
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if re.match(r"\[(dependencies|dev-dependencies|build-dependencies)\]", stripped):
                in_deps = True
                continue
            if stripped.startswith("[") and "dependencies" not in stripped:
                in_deps = False
            if in_deps:
                m = re.match(r'^([a-zA-Z0-9_\-]+)\s*=', stripped)
                if m:
                    deps.append(m.group(1).lower())
    except Exception:
        pass
    return deps


def parse_go_mod(content: str) -> list[str]:
    """Extract require block module paths from go.mod."""
    deps = []
    if not content:
        return deps
    try:
        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if stripped == ")":
                in_require = False
                continue
            # Single-line require
            m = re.match(r"require\s+(\S+)", stripped)
            if m:
                module_path = m.group(1)
                # Extract last path component as the dep name
                deps.append(module_path.split("/")[-1].lower())
                continue
            if in_require and stripped and not stripped.startswith("//"):
                parts = stripped.split()
                if parts:
                    module_path = parts[0]
                    deps.append(module_path.split("/")[-1].lower())
    except Exception:
        pass
    return list(dict.fromkeys(deps))


def _parse_file(filename: str, content: str) -> list[str]:
    """Dispatch to the appropriate parser for a filename."""
    fname = filename.lower()
    if fname == "requirements.txt" or fname.startswith("requirements-"):
        return parse_requirements_txt(content)
    elif fname == "pyproject.toml":
        return parse_pyproject_toml(content)
    elif fname == "setup.cfg":
        return parse_requirements_txt(content)  # similar format
    elif fname == "cmakelists.txt":
        return parse_cmake(content)
    elif fname == "package.json":
        return parse_package_json(content)
    elif fname == "cargo.toml":
        return parse_cargo_toml(content)
    elif fname == "go.mod":
        return parse_go_mod(content)
    return []


async def scrape_repo_deps(
    client: GitHubClient,
    cache: Cache,
    org: str,
    repo: str,
) -> dict[str, list[str]]:
    """Fetch and parse all dep files for a single repo."""
    results: dict[str, list[str]] = {}

    for filename in DEP_FILES:
        # Check cache first
        cached = cache.get_dep(org, repo, filename)
        if cached is not None:
            content = cached
        else:
            content = await client.get_file(org, repo, filename)
            if content is None:
                continue
            cache.put_dep(org, repo, filename, content)

        parsed = _parse_file(filename, content)
        if parsed:
            results[filename] = parsed

    return results


async def scrape_all(
    client: GitHubClient,
    cache: Cache,
    repos: list[dict],
    min_stars: int = 50,
) -> dict[str, dict]:
    """Scrape deps for all repos above min_stars threshold."""
    results: dict[str, dict] = {}

    for repo in repos:
        if repo.get("stars", 0) < min_stars:
            continue
        repo_id = repo["id"]
        org = repo["org"]
        name = repo["name"]

        try:
            deps = await scrape_repo_deps(client, cache, org, name)
            if deps:
                results[repo_id] = deps
        except Exception as e:
            import sys
            print(f"Warning: dep scrape failed for {repo_id}: {e}", file=sys.stderr)

    return results
