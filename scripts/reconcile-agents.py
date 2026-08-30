#!/usr/bin/env python3
"""Archive active dossiers after their authority rows are removed."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "sub-agents" / "active"
INACTIVE = ROOT / "sub-agents" / "inactive"
TABLE = ROOT / "sub-agents" / "active.md"


def declared_agent_ids() -> set[str]:
    text = TABLE.read_text(encoding="utf-8")
    return set(re.findall(r"^\|\s*([a-z0-9][a-z0-9-]*)\s*\|", text, re.MULTILINE))


def archive(agent_id: str) -> None:
    subprocess.run(
        ["tmux", "kill-session", "-t", f"orchestrator-{agent_id}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = INACTIVE / f"{agent_id}-{stamp}"
    if destination.exists():
        raise RuntimeError(f"archive destination already exists: {destination}")
    shutil.move(str(ACTIVE / agent_id), destination)
    print(f"archived {agent_id} -> {destination.relative_to(ROOT)}")


def main() -> None:
    declared = declared_agent_ids()
    for dossier in sorted(ACTIVE.iterdir()):
        if dossier.is_dir() and dossier.name not in declared:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", dossier.name):
                raise RuntimeError(f"invalid active dossier name: {dossier.name}")
            archive(dossier.name)


if __name__ == "__main__":
    main()
