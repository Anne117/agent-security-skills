#!/usr/bin/env python3
"""Find likely secrets in a tree without ever printing them.

Usage:
    python3 scan_secrets.py <path> [--json]

Prints one line per match: file:line, rule, masked preview, length.
Exit code 1 if anything was found, 0 if clean, 2 on usage error.

Matching is heuristic. A clean run is not proof that no secret exists.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

RULES = [
    ("aws_access_key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("telegram_bot", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("google_api", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe_key", re.compile(r"\b(sk|rk)_(live|test)_[0-9A-Za-z]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("env_assignment", re.compile(r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY)[A-Z0-9_]*\s*=\s*['\"]?([^\s'\"#]{8,})")),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".gz", ".tar",
            ".mp4", ".mov", ".woff", ".woff2", ".ttf", ".ico", ".lock"}
MAX_BYTES = 2 * 1024 * 1024


def mask(value: str) -> str:
    v = value.strip().strip("'\"")
    if len(v) <= 8:
        return "*" * len(v)
    return v[:4] + "*" * min(10, len(v) - 8) + v[-2:]


def entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((c / len(s)) * math.log2(c / len(s)) for c in counts.values())


def scan(path: Path):
    findings = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SKIP_EXT:
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if len(line) > 4000:
                continue
            seen_here = set()
            for name, rx in RULES:
                for m in rx.finditer(line):
                    raw = m.group(1) if name == "env_assignment" else m.group(0)
                    if raw in seen_here:
                        continue
                    seen_here.add(raw)
                    findings.append({
                        "file": str(p), "line": lineno, "rule": name,
                        "preview": mask(raw), "length": len(raw),
                        "entropy": round(entropy(raw), 2),
                    })
            if seen_here:
                continue  # провайдерское правило уже нашло секрет в этой строке
            for token in re.findall(r"[A-Za-z0-9_\-+/=]{24,}", line):
                if entropy(token) > 4.2 and not token.lower().startswith(("http", "sha256")):
                    findings.append({
                        "file": str(p), "line": lineno, "rule": "high_entropy",
                        "preview": mask(token), "length": len(token),
                        "entropy": round(entropy(token), 2),
                    })
    return findings


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    root = Path(args[0]).expanduser().resolve()
    if not root.exists():
        print(f"no such path: {root}", file=sys.stderr)
        return 2
    findings = scan(root)
    if "--json" in sys.argv:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}  {f['rule']:<16} {f['preview']}  "
                  f"len={f['length']} entropy={f['entropy']}")
        print(f"\n{len(findings)} potential secret(s). Values are masked on purpose.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
