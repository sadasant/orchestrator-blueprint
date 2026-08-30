#!/usr/bin/env python3
"""Check blueprint privacy, Markdown structure, and repository hygiene."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def repository_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        files.append(path)
    return sorted(files)


def text_files(paths: list[Path]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path in paths:
        try:
            result[path] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return result


def check_markdown(texts: dict[Path, str], errors: list[str]) -> None:
    for path, text in texts.items():
        if path.suffix != ".md":
            continue
        first_lines = "\n".join(text.splitlines()[:8])
        if "> **Brief:**" not in first_lines:
            errors.append(f"Markdown file lacks an opening Brief: {path.relative_to(ROOT)}")


def check_privacy(texts: dict[Path, str], errors: list[str]) -> None:
    patterns = {
        "absolute macOS home path": re.compile("/" + "Users" + r"/[^/\s]+/"),
        "absolute Linux home path": re.compile("/" + "home" + r"/[^/\s]+/"),
        "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        "private key material": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "GitHub-style token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "API-key-like token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "credential in URL": re.compile(r"https?://[^/\s:@]+:[^/\s@]+@"),
    }
    forbidden_terms = {
        "reserved personal name": "dan" + "iel",
        "source account name": "sada" + "sant",
        "superseded credential broker": "eng" + "ram",
    }
    for path, text in texts.items():
        relative = path.relative_to(ROOT)
        for label, pattern in patterns.items():
            if pattern.search(text):
                errors.append(f"{label} found in {relative}")
        lowered = text.lower()
        for label, term in forbidden_terms.items():
            if term in lowered:
                errors.append(f"{label} found in {relative}")


def check_runtime_artifacts(paths: list[Path], errors: list[str]) -> None:
    for path in paths:
        relative = path.relative_to(ROOT)
        if path.name == "runner.log":
            errors.append(f"raw runner log is present: {relative}")
        if path.is_symlink() and os.path.isabs(os.readlink(path)):
            errors.append(f"absolute symlink is present: {relative}")


def check_executables(paths: list[Path], errors: list[str]) -> None:
    for path in paths:
        relative = path.relative_to(ROOT)
        should_execute = (
            relative.parts[0] == "scripts"
            and path.suffix in {".sh", ".py"}
            and path.name != "_runtime.sh"
        ) or (
            relative.parts[0] == "harnesses"
            and path.suffix == ".sh"
            and not path.name.endswith(".example.sh")
        )
        if should_execute and not path.stat().st_mode & stat.S_IXUSR:
            errors.append(f"expected executable mode: {relative}")


def main() -> None:
    paths = repository_files()
    texts = text_files(paths)
    errors: list[str] = []
    check_markdown(texts, errors)
    check_privacy(texts, errors)
    check_runtime_artifacts(paths, errors)
    check_executables(paths, errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"checked {len(paths)} files: privacy and structure passed")


if __name__ == "__main__":
    main()
