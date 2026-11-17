#!/usr/bin/env python3
"""Validate SKILL.md files in this repo: frontmatter, naming, required sections.

Usage: python3 scripts/validate_skills.py [skills_dir]
Exit 1 on any problem.
"""
from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_KEYS = ("name", "description", "version", "license")
REQUIRED_SECTIONS = ("## When to use", "## Pitfalls")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip().splitlines()
    data = {}
    for line in raw:
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
    return data, text[end + 4:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "skills")
    problems = []
    count = 0
    for skill in sorted(root.glob("*/SKILL.md")):
        count += 1
        text = skill.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        for key in REQUIRED_KEYS:
            if not fm.get(key):
                problems.append(f"{skill}: missing frontmatter key '{key}'")
        if fm.get("name") and fm["name"] != skill.parent.name:
            problems.append(f"{skill}: name '{fm['name']}' != folder '{skill.parent.name}'")
        if len(body) < 800:
            problems.append(f"{skill}: body looks too short ({len(body)} chars)")
        for section in REQUIRED_SECTIONS:
            if section not in body:
                problems.append(f"{skill}: missing section '{section}'")
        if "TODO" in text or "TBD" in text:
            problems.append(f"{skill}: contains TODO/TBD")
    print(f"checked {count} skill(s)")
    for p in problems:
        print("  ✗", p)
    if not problems:
        print("  ✓ all good")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
