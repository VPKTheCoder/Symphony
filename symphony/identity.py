"""Stable repository identity used by analysis and composition."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def make_repo_fingerprint(repo_name: str, modules: list[dict[str, Any]]) -> str:
    structure = [
        {
            "name": item["name"],
            "loc": item.get("loc", 0),
            "complexity": item.get("complexity", 0.0),
            "unsafe_count": item.get("unsafe_count", 0),
            "depends_on": sorted(item.get("depends_on", [])),
            "depended_by_count": item.get("depended_by_count", 0),
            "todo_count": item.get("todo_count", 0),
        }
        for item in sorted(modules, key=lambda value: value["name"])
    ]
    payload = json.dumps(
        {"repo": repo_name, "modules": structure},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def profile_fingerprint(profile) -> str:
    if profile.repo_fingerprint:
        return profile.repo_fingerprint
    return make_repo_fingerprint(
        profile.name,
        [
            {
                "name": module.name,
                "loc": module.loc,
                "complexity": module.complexity,
                "unsafe_count": module.unsafe_count,
                "depends_on": list(module.depends_on),
                "depended_by_count": module.depended_by_count,
                "todo_count": module.todo_count,
            }
            for module in profile.modules
        ],
    )


def variation_seed(profile, style_name: str, variation_index: int) -> int:
    payload = f"{profile_fingerprint(profile)}:{style_name}:{variation_index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
