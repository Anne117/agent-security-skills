# Agent security skills

Four skills for reviewing AI agents: threat models, MCP configs, leaked
secrets and prompt injection. Written to be executed by an agent, not skimmed
by a human — every skill has a procedure, checklists, an output format and a
list of pitfalls.

[![License: MIT](https://img.shields.io/badge/license-MIT-4ade80.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-4-a78bfa.svg)](#skills)

## Skills

| Skill | Use it when | Output |
|---|---|---|
| [`agent-threat-model`](skills/agent-threat-model/SKILL.md) | an agent is about to get tools, data or money | assets, capability table, attack paths, ranked controls |
| [`mcp-hardening`](skills/mcp-hardening/SKILL.md) | adding or reviewing an MCP server | red flags, risk table, hardened config diff, verification |
| [`secrets-hygiene`](skills/secrets-hygiene/SKILL.md) | a repo or bundle may contain a live credential | masked findings, containment order, history cleanup, prevention |
| [`prompt-injection-review`](skills/prompt-injection-review/SKILL.md) | a prompt or skill ingests untrusted content | instruction-source map, weaknesses, rewrites, test results |

Each skill follows the same shape: **when to use → procedure → verification →
report template → pitfalls**. None of them claim to prove safety; each states
what it did not check.

## Install

The skills use the open `SKILL.md` format and work with any agent that supports
it.

**Hermes**

```bash
git clone https://github.com/Anne117/agent-security-skills.git
cp -r agent-security-skills/skills/* ~/.hermes/skills/security/
```

**Claude Code / Cursor / other agents** — copy the skill folder into the
agent's skills directory, or point it at the `SKILL.md` file. The frontmatter
carries the trigger description, so the agent knows when to load it.

## Validate

```bash
python3 scripts/validate_skills.py
```

Checks frontmatter keys, folder/name match, minimum body length, required
sections and leftover TODO markers.

## Test the secret scanner

The scanner masks every value it prints — it never echoes a credential.

```bash
python3 skills/secrets-hygiene/scripts/scan_secrets.py /path/to/repo
python3 skills/secrets-hygiene/scripts/scan_secrets.py /path/to/repo --json
```

Exit code `1` means something was found, `0` clean, `2` usage error.

## What these skills are not

- not a penetration test;
- not a compliance certification;
- not a guarantee that an agent is safe;
- not a replacement for reading the third-party code you connect.

They are structured review procedures that make an agent's security work
repeatable, reviewable and honest about its own gaps.

## License

MIT — see [LICENSE](LICENSE).
