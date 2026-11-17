---
name: agent-deployment-gate
description: "Use before an AI agent goes to production, or before its permissions are widened."
version: 1.0.0
author: Anne Arintseva
license: MIT
metadata:
  hermes:
    tags: [security, deployment, gate, review, ai-agents, compliance]
    editorial_name: Agent deployment gate
    editorial_description: A go/no-go gate with evidence requirements across identity, capability, data, injection, observability and supply chain — plus waivers, rollback and sign-off.
    requires_tools: [terminal, read_file, write_file]
    requires_toolsets: [terminal]
---

# Agent deployment gate

Use this skill when an agent moves to production, gets new tools, or has its
permissions widened. The gate produces a signed decision: **go**, **go with
conditions**, or **no-go**.

The gate is only as good as its evidence. Self-attestation ("we checked") is not
evidence. Every P0 item needs an artifact: a command output, a config line, a
test result with a timestamp.

## When to use

- first production deploy of an agent;
- adding filesystem, network, database, payment or email capability;
- switching an agent from human-in-the-loop to autonomous;
- a customer or auditor asks how the agent was approved;
- after an incident, before the agent is re-enabled.

## Gate principles

1. **Evidence or it did not happen.** Each item links to an artifact.
2. **P0 blocks.** One failed P0 means no-go, regardless of everything else.
3. **Waivers expire.** A waiver has an owner, a reason, a compensating control
   and a hard expiry date. No open-ended exceptions.
4. **The gate is re-run on change.** New tool, new MCP server, new model with
   broader behaviour, new data source → gate again.
5. **Separate the reviewer from the author.** The person who built the agent does
   not sign off alone.

## Domains and requirements

### 1. Identity and access

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| ID-1 | P0 | Agent has its own identity, not a human's personal token | token/service account name, owner, creation date |
| ID-2 | P0 | Scope is minimal for the task (one repo / one bucket / one env) | IAM policy or token scopes, diff against previous |
| ID-3 | P1 | Credentials expire and rotate on a schedule | expiry config, rotation runbook link |
| ID-4 | P1 | Separate credentials per environment | secret names per env, no shared values |

### 2. Capability

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| CAP-1 | P0 | Every tool is listed with read/write/network/exec capability | capability table from `agent-threat-model` |
| CAP-2 | P0 | Destructive tools require human approval | approval config, screenshot of a blocked action |
| CAP-3 | P0 | No write access to the agent's own prompt, skills or config | file permissions test result |
| CAP-4 | P1 | Egress restricted to an allowlist | proxy/firewall rule, test call to a non-listed host fails |
| CAP-5 | P1 | Runtime sandbox: read-only FS, writable scratch dir | container flags, mount list |

### 3. Data

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| DATA-1 | P0 | Sensitive paths denied at the tool layer (`~/.ssh`, `~/.aws`, `.env`) | deny rule + test call returning an error |
| DATA-2 | P0 | Classified data inventory: what the agent can read | table with classes and volumes |
| DATA-3 | P1 | Retention and deletion defined for agent traces | retention config, deletion job |
| DATA-4 | P1 | PII minimisation: no full records in prompts when a summary suffices | prompt sample, redaction code |

### 4. Injection and untrusted content

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| INJ-1 | P0 | Instruction hierarchy declared; tool output treated as data | prompt version + excerpt |
| INJ-2 | P0 | Injection test suite executed against the real tool-enabled agent | 8 test cases with tool-call logs |
| INJ-3 | P1 | False-refusal rate measured on benign content | test results, percentage |
| INJ-4 | P1 | Output handling: no raw untrusted HTML/markdown rendered into privileged UI | rendering code path |

### 5. Observability

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| OBS-1 | P0 | Every tool call logged: timestamp, tool, args hash, result size, identity | log sample |
| OBS-2 | P0 | Kill switch tested within the last 30 days | test record with time and operator |
| OBS-3 | P1 | Alerts on: egress to new host, credential file access, destructive tool, spend spike | alert rules |
| OBS-4 | P1 | Traces retained long enough to investigate an incident (≥30 days) | retention setting |

### 6. Supply chain

| ID | Pri | Requirement | Evidence |
|---|---|---|---|
| SC-1 | P0 | All skills and MCP servers reviewed with `veyra` or `mcp-hardening` | scan report link, date |
| SC-2 | P0 | Versions pinned; no `latest` / `npx -y` without a version | config diff |
| SC-3 | P1 | Dependencies reviewed with `dependency-risk-review` | verdict table |
| SC-4 | P1 | Agent image built from a pinned digest, SBOM generated | image digest, SBOM file |

## How to verify (examples)

Each item needs a check someone else can repeat.

```bash
# ID-2: token scope
gh api /user --jq .login && gh api /installation/repositories --jq '.repositories[].full_name'

# CAP-3: agent cannot write its own config
sudo -u agent test -w /srv/agent/config && echo "WRITABLE (fail)" || echo "not writable (pass)"

# DATA-1: deny rule works
tool_read_file ~/.ssh/id_rsa    # must return an error, not a key

# CAP-4: egress allowlist
curl -sS https://example.com    # must fail from the agent's network namespace

# OBS-2: kill switch
./scripts/disable-agent.sh && ./scripts/verify-agent-down.sh
```

Record the exact command and its output hash. "Verified" without a command is a
claim, not evidence.

## Waivers

A waiver is allowed only for P1 items, never P0.

```
Waiver: <ID>            Owner: <name>          Expires: <YYYY-MM-DD>
Reason: <why it cannot be fixed before launch>
Compensating control: <what reduces the risk meanwhile>
Verification: <how the control is checked>
Approved by: <security reviewer>, <date>
```

Expired waivers fail the gate automatically. A waiver renewed twice without a
fix is escalated, not renewed a third time.

## Gate report

```
Agent: <name> <version>        Environment: <prod/stage>
Reviewers: <names>             Date: <UTC>
Model: <name/version>          Prompt: <hash/version>
Skills: <list + scan report>   MCP: <list + config hash>

Result: GO | GO WITH CONDITIONS | NO-GO

P0 failures: <IDs, or "none">
P1 failures: <IDs>
Waivers: <IDs with expiry>
Conditions: <what must be true before traffic, with owner and time>

Evidence index:
  ID-1  <artifact path / URL>  sha256:<hash>  <timestamp>
  ...
```

## Go / conditional / no-go

- **GO** — all P0 pass; P1 pass or waived with a valid expiry.
- **GO WITH CONDITIONS** — all P0 pass, and the conditions are mechanical
  (e.g. "egress allowlist enabled before traffic", "kill switch test repeated").
  Conditions have an owner and a deadline; the gate is re-checked when they are
  due.
- **NO-GO** — any P0 failure, or a P1 failure without a valid waiver, or evidence
  that cannot be reproduced.

## Re-gate triggers

Run the gate again when any of these change:

- a new tool or MCP server is added;
- the model changes version or provider;
- the prompt changes in a way that alters capability (new instructions to act);
- permissions or scopes are widened;
- an incident occurs (always re-gate before re-enabling);
- 90 days pass with no review.

## Pitfalls

- Signing off on a demo. Test the production configuration, with production
  tools and production data classes.
- Accepting screenshots as evidence. Prefer command output and config lines that
  can be re-run.
- Treating the gate as a one-time event. Agents change weekly; the gate must
  follow the change.
- Writing conditions like "improve monitoring". A condition is a check with a
  pass/fail result.
- Letting the author approve their own work. Independence is the point.
- Passing P0 injection tests on a chat interface while the production agent has
  tools. The tools are what make injection dangerous.
