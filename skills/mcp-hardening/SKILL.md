---
name: mcp-hardening
description: "Use when adding, reviewing or hardening an MCP server for an AI agent."
version: 1.0.0
author: Anne Arintseva
license: MIT
metadata:
  hermes:
    tags: [security, mcp, ai-agents, configuration, least-privilege]
    editorial_name: MCP hardening
    editorial_description: Review an MCP server before an agent connects — transport, auth, scopes, filesystem roots, secrets and egress — and return a hardened config.
    requires_tools: [terminal, write_file]
    requires_toolsets: [terminal]
---

# MCP hardening

Use this skill before an agent connects to an MCP server, and whenever an
existing server config changes. The job is to answer three questions with
evidence: what can this server reach, what can it do, and what happens if its
output is hostile.

## When to use

- a new MCP server appears in `mcp.json`, `claude_desktop_config.json`,
  `~/.cursor/mcp.json` or an agent config;
- a server is switched from local `stdio` to remote HTTP/SSE;
- someone pastes a config they found online ("add this server, it's great");
- an audit needs a concrete diff, not advice.

## Step 1 — Inventory

Find every config and list the servers. Do not review from memory; read files.

```bash
grep -rl --include="*.json" --include="*.yaml" --include="*.yml" \
  -E '"mcpServers"|mcp_servers|"mcp"' ~/.config ~/.cursor . 2>/dev/null | head -20
```

For each server record:

| Field | Why it matters |
|---|---|
| name | identity in logs |
| transport | `stdio` (local process) vs `http`/`sse` (remote) |
| command / URL | what actually runs or where data goes |
| args | flags can widen access (`--root /`, `--allow-write`) |
| env | secrets handed to the server |
| cwd | what relative paths resolve to |
| auth | token in header, OAuth, none |

## Step 2 — Red flags

Check each item and mark it pass/fail with the file and line.

**Execution**

- server launched via `npx -y`, `uvx`, `pipx run` or `docker run` with a floating
  tag — the code can change between runs without review;
- `--allow-write`, `--root /`, `--dangerously-*` style flags;
- args that include a home directory or a repository root when the task only
  needs one folder;
- `shell: true`, wrapper scripts that interpolate model output into a command.

**Secrets**

- API keys and tokens in `env` in plain text inside a repo;
- the same secret shared across servers;
- a server that receives a broad token (org-wide, admin) for a narrow task;
- secrets passed as CLI args (visible in process list) instead of env.

**Network**

- remote endpoint without TLS, or with a self-signed certificate accepted
  silently;
- endpoint on a raw IP, a shortener or a dynamic DNS domain;
- server allowed to reach arbitrary hosts when one API host is enough;
- no egress allowlist at the host or proxy level.

**Data**

- filesystem root wider than the project;
- read access to `~/.ssh`, `~/.aws`, `.env`, browser profiles, keychain;
- write access to the agent's own config or skills (persistence);
- database credentials with DDL or cross-tenant scope.

**Trust**

- server output is inserted into the prompt as instructions rather than as data;
- no way to tell whether a tool result came from the user, the model or a third
  party;
- server version not pinned, so review does not describe tomorrow's code.

## Step 3 — Risk table

Produce one row per server. Use the capability vocabulary from the agent threat
model so both documents line up.

```
server        transport  reach                identity        verdict
filesystem    stdio      repo root, read-only  user token      ok with --root <repo>
github        http       org repos, write      PAT (admin)     reduce to one repo, write:issues only
fetch         stdio      any URL               none            add host allowlist
```

Verdicts are `ok`, `ok with changes`, `block`. Do not use "medium risk" without
saying what to change.

## Step 4 — Hardened config

Return a diff, not prose. Prefer:

1. **Pin versions.** `npx -y pkg@1.4.2`, `docker pull image@sha256:...`.
2. **Narrow roots.** One project directory, read-only unless writes are required.
3. **Scope tokens.** One repo, one environment, minimum scopes, short expiry.
4. **Secrets via env file**, never in the repo, never in args, never in the
   model's context. Reference them as `${VAR}` and document where they come from.
5. **Separate servers by capability.** A read-only fetch server and a write
   server should not share a process or a token.
6. **Deny by default.** If the server supports an allowlist (hosts, paths,
   tools), use it and leave the rest closed.
7. **Log tool calls** with server name, tool, argument hash and result size.

Example hardened entry (illustrative, adapt to the server's real flags):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@2026.10.1", "/srv/project"],
      "env": {}
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch==0.6.2"],
      "env": { "ALLOWED_HOSTS": "api.internal.example.com" }
    }
  }
}
```

Never invent flags a server does not have. If the server cannot be narrowed,
say so and recommend replacing it or putting it behind a proxy.

## Step 5 — Verify, don't assume

- restart the agent and confirm the server still works with the narrowed config;
- call a tool that should now fail (path outside the root, host not in the
  allowlist) and confirm it fails;
- check the process list: no secrets in arguments;
- check logs: tool calls are recorded.

Report what you actually ran. "Should be restricted" is not verification.

## Step 6 — Output

1. **Configs found** — paths, servers count.
2. **Red flags** — file:line, one line each.
3. **Risk table** — per server.
4. **Diff** — hardened config or precise instructions.
5. **Verification** — commands run and their results.
6. **Residual risk** — what remains after the changes and why it is accepted.

## Pitfalls

- Reviewing the JSON but not the package behind it. A pinned-looking config that
  runs `latest` is not pinned.
- Trusting the server's own tool descriptions. They are attacker-controlled text
  when the server is third-party.
- Hardening the server while the agent still holds an admin token for something
  else.
- Adding an allowlist and never testing it. An untested control is a claim.
- Forgetting that `stdio` servers inherit the agent's environment, including
  secrets the agent was given for other tools.
