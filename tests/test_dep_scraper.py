"""Tests for dep_scraper parsers."""
from __future__ import annotations

import pytest
from repo_hub.fetcher.dep_scraper import (
    parse_cargo_toml,
    parse_cmake,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
)


class TestParseRequirementsTxt:
    def test_basic(self):
        content = "torch\nnumpy\npandas\n"
        deps = parse_requirements_txt(content)
        assert "torch" in deps
        assert "numpy" in deps

    def test_comments_stripped(self):
        content = "# This is a comment\ntorch>=2.0  # inline comment\nnumpy\n"
        deps = parse_requirements_txt(content)
        assert "torch" in deps
        assert "numpy" in deps
        assert "# This is a comment" not in deps

    def test_version_specs_stripped(self):
        content = "torch>=2.0.0\nnumpy==1.24.0\npandas~=2.0\n"
        deps = parse_requirements_txt(content)
        assert "torch" in deps
        assert "numpy" in deps
        assert "pandas" in deps
        # No version strings
        for dep in deps:
            assert ">=" not in dep and "==" not in dep

    def test_extras_stripped(self):
        content = "psycopg[binary]>=3.1\nhttpx[http2]\n"
        deps = parse_requirements_txt(content)
        assert "psycopg" in deps
        assert "httpx" in deps

    def test_skip_flags(self):
        content = "-r other-requirements.txt\n--index-url https://...\ntorch\n"
        deps = parse_requirements_txt(content)
        assert "torch" in deps
        assert "-r" not in deps

    def test_empty_content(self):
        assert parse_requirements_txt("") == []

    def test_malformed_graceful(self):
        # Should not raise
        result = parse_requirements_txt("!!invalid!!\n@@@\ntorch\n")
        assert isinstance(result, list)


class TestParsePyprojectToml:
    def test_pep621_format(self):
        content = """
[project]
name = "mypackage"
dependencies = [
    "torch>=2.0",
    "numpy",
    "transformers[torch]",
]
"""
        deps = parse_pyproject_toml(content)
        assert "torch" in deps
        assert "numpy" in deps
        assert "transformers" in deps

    def test_poetry_format(self):
        content = """
[tool.poetry.dependencies]
python = "^3.11"
torch = "^2.0"
numpy = "*"
"""
        deps = parse_pyproject_toml(content)
        assert "torch" in deps
        assert "numpy" in deps
        assert "python" not in deps

    def test_empty(self):
        assert parse_pyproject_toml("") == []

    def test_malformed_graceful(self):
        result = parse_pyproject_toml("not valid toml @@@@")
        assert isinstance(result, list)


class TestParseCmake:
    def test_find_package(self):
        content = """
cmake_minimum_required(VERSION 3.20)
find_package(LLVM REQUIRED CONFIG)
find_package(MLIR REQUIRED CONFIG)
"""
        deps = parse_cmake(content)
        assert "LLVM" in deps
        assert "MLIR" in deps

    def test_fetchcontent(self):
        content = """
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
"""
        deps = parse_cmake(content)
        assert "googletest" in deps

    def test_empty(self):
        assert parse_cmake("") == []


class TestParsePackageJson:
    def test_dependencies(self):
        import json
        content = json.dumps({
            "name": "my-app",
            "dependencies": {
                "react": "^18.0.0",
                "webgpu": "^1.0.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
            }
        })
        deps = parse_package_json(content)
        assert "react" in deps
        assert "webgpu" in deps
        assert "typescript" in deps

    def test_empty(self):
        assert parse_package_json("") == []

    def test_malformed(self):
        result = parse_package_json("{invalid json")
        assert isinstance(result, list)


class TestParseCargoToml:
    def test_dependencies(self):
        content = """
[package]
name = "my-crate"

[dependencies]
serde = { version = "1", features = ["derive"] }
tokio = "1"

[dev-dependencies]
criterion = "0.5"
"""
        deps = parse_cargo_toml(content)
        assert "serde" in deps
        assert "tokio" in deps
        assert "criterion" in deps

    def test_empty(self):
        assert parse_cargo_toml("") == []


class TestParseGoMod:
    def test_require_block(self):
        content = """
module github.com/myorg/myproject

go 1.21

require (
    github.com/spf13/cobra v1.7.0
    golang.org/x/net v0.12.0
    github.com/stretchr/testify v1.8.4 // indirect
)
"""
        deps = parse_go_mod(content)
        assert "cobra" in deps
        assert "net" in deps or "x" in deps

    def test_single_require(self):
        content = "require github.com/pkg/errors v0.9.1\n"
        deps = parse_go_mod(content)
        assert "errors" in deps

    def test_empty(self):
        assert parse_go_mod("") == []
