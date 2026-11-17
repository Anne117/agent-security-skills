---
name: agent-incident-response
description: "Use when an AI agent has already done something harmful and the response must be run, not improvised."
version: 1.0.0
author: Anne Arintseva
license: MIT
metadata:
  hermes:
    tags: [security, incident-response, ai-agents, forensics, runbook]
    editorial_name: Agent incident response
    editorial_description: A phase-by-phase runbook for agent incidents — declare, capture evidence, contain, eradicate, recover, and write a postmortem that survives audit.
    requires_tools: [terminal, write_file]
    requires_toolsets: [terminal]
---

# Agent incident response

Use this skill when an agent may have already acted: leaked data, called an
external endpoint, deleted or modified resources, ran a command it should not
have, sent messages to customers, or spent money.

This is a runbook, not a discussion. Follow the phases in order. Every action
gets a timestamp and an owner. If you skip a step, write down why.

## When to use

- an alert fires on agent behaviour (unexpected egress, mass deletion, new
  deploy key, billing spike, data in an outbound request);
- a user reports that the agent "sent something it shouldn't have";
- prompt-injection is suspected after the agent read untrusted content;
- a credential used by the agent appears in a public place.

If nothing has happened yet and you are only reviewing, use
`agent-threat-model` instead.

## Severity and clock

Decide the severity in the first five minutes. It drives everything else.

| SEV | Definition | Examples | First response | Update cadence |
|---|---|---|---|---|
| SEV1 | Confirmed data loss, production access, or money movement | customer records exfiltrated, prod DB dropped, payments sent | 15 min | every 30 min |
| SEV2 | Confirmed unauthorized action, contained blast radius | repo made public, messages sent to one customer, token created | 30 min | hourly |
| SEV3 | Suspicious behaviour, no confirmed impact | anomalous egress blocked, agent looping on a sensitive path | 2 h | daily |
| SEV4 | Policy deviation, no impact | agent used a tool outside its intended scope | next business day | at closure |

Write the declared severity, the time, and who declared it. Severity can go up;
it can go down only with evidence, and the reason is recorded.

## Phase 0 — Before anything (5 minutes)

These are the facts you need in hand. If they are unknown, say so; do not stall.

- [ ] Who is the incident commander (IC)? One name, not a group.
- [ ] Who owns the agent's credentials and can revoke them right now?
- [ ] Where are the logs: agent trace, tool calls, HTTP egress, auth, CI?
- [ ] What is the kill switch: disable the agent, revoke the token, block egress?
- [ ] Who talks to customers / legal / leadership?

Open a single incident document. Every fact goes there with a timestamp and a
source. Chat is not the record.

## Phase 1 — Detect and capture (first 15 minutes)

**Capture before you clean.** Restarting the agent, deleting a container or
rotating a token destroys the evidence you will need.

Capture, in this order:

1. **Agent trace** — the full session transcript, including tool calls and
   arguments. Export it, do not screenshot it.
2. **Tool-call log** — timestamp, tool, arguments hash, result size, identity.
3. **Egress logs** — proxy, firewall, DNS, cloud flow logs for the window.
4. **Identity events** — token creation, key upload, role changes, logins.
5. **State** — container image digest, config files, skill versions, model and
   prompt version.
6. **Hashes** — `sha256sum` of every exported artifact; record them.

Write the capture window: start and end timestamps in UTC, and why that window.

If the agent is still running and actively causing harm, containment (phase 3)
comes before full capture — but take the trace snapshot first, it is cheap.

## Phase 2 — Triage (30 minutes)

Answer these, with evidence:

1. **What did it do?** List actions, not intentions.
2. **With whose identity?** Which token, whose permissions, what scope.
3. **From what input?** Which content or instruction triggered it.
4. **What is the blast radius?** Systems, data classes, number of records.
5. **Is it still happening?** Evidence of ongoing calls or scheduled work.
6. **Who else is affected?** Customers, partners, other agents sharing tokens.

If you cannot answer 1–3 with evidence, the severity is at least SEV2 and you
contain first.

## Phase 3 — Contain (ordered)

Do these in order. Each one is reversible where possible.

1. **Stop the action, not the evidence.** Disable the agent's ability to act:
   revoke its token, disable the tool, block egress at the proxy. Prefer
   revocation over killing the process, so the trace stays readable.
2. **Revoke derived credentials.** Sessions, refresh tokens, deploy keys,
   webhooks, OAuth grants created in the window.
3. **Isolate the runtime.** Remove network access; keep the filesystem for
   forensics.
4. **Freeze the blast radius.** Make affected repos private, pause pipelines,
   disable the payment integration, lock the bucket ACL.
5. **Preserve copies.** Snapshot disks and logs to a read-only location with
   hashes.
6. **Notify the owner of each affected system**, even if it looks minor.

Containment is done when the agent can no longer repeat the action, proven by a
test attempt that fails.

## Phase 4 — Eradicate

- Find the **entry point**: injected content, malicious skill, over-broad token,
  misconfigured MCP server, missing approval gate.
- Confirm it with evidence: the exact file:line, the exact prompt fragment, the
  exact tool argument.
- Remove or fix it; if the fix is a config change, record the before/after.
- Check for the same pattern in other agents, other environments and other
  repos. One incident is rarely one instance.

Do not close eradication while the root cause is a hypothesis.

## Phase 5 — Recover

1. Restore from a known-good state, not from the compromised one.
2. Re-issue credentials with the minimum scope needed; short expiry.
3. Enable the monitoring that would have caught this earlier.
4. Run the agent against a benign test suite, plus the injection cases from
   `prompt-injection-review`.
5. Watch for recurrence for a defined period (24 h for SEV2+, 7 days for SEV1),
   with an owner and an alert.

Recovery is done when the agent works, the controls are on, and the watch period
has passed without recurrence.

## Phase 6 — Postmortem (within 5 business days)

Blameless. Facts, decisions, gaps. Template:

```
Incident: <id>            Severity: <SEV>        Duration: <start>–<end> UTC
Commander: <name>         Systems: <list>        Data: <classes, volumes>

Summary (3 sentences)

Timeline (UTC, one line per event, source in brackets)
  12:03  alert: egress to unknown host [proxy log]
  12:07  IC declared SEV2 [incident doc]
  ...

What happened (mechanism, not blame)
What allowed it (missing control, not "human error")
What worked
What delayed detection and response (minutes per step)
Actions: owner, due date, verification method
Residual risk accepted, by whom, until when
```

Every action item needs an owner and a way to verify it was done. "Improve
monitoring" is not an action; "alert when tool X is called with a path outside
/repo, verified by test call" is.

## Evidence handling

- Keep originals read-only; work on copies.
- Record `sha256` and file size for every artifact.
- Never edit a log to remove a secret; redact on export and note the redaction.
- Store evidence with access control and a retention date.
- If regulators or customers may need it, assume the record will be read by
  someone outside the team: write it that way.

## Communication

- **Internal:** severity, impact, what is contained, what is next, next update
  time. No speculation about cause.
- **Customer:** what they need to do, if anything; facts confirmed; when the next
  update comes. Do not minimize and do not guess.
- **Legal/regulator:** hand over the timeline and evidence index; do not
  paraphrase data volumes.
- **Public:** only after legal review; one voice.

## Exit criteria

| Phase | Done when |
|---|---|
| Capture | trace, tool calls, egress and identity events exported and hashed |
| Contain | a repeat attempt fails, verified |
| Eradicate | root cause has a file:line or a config diff, not a theory |
| Recover | controls on, watch period passed, no recurrence |
| Postmortem | actions have owners, dates and verification methods |

## Pitfalls

- Restarting or redeploying first. It destroys the trace and looks like hiding.
- Rotating one token while derived sessions and deploy keys stay valid.
- Treating "the model was confused" as a root cause. The cause is the missing
  gate, the over-broad token or the untrusted input path.
- Declaring containment without a failed retry test.
- Writing a postmortem with "be more careful" as an action.
- Forgetting other agents that share the same credentials or the same skill.
- Reporting data volumes you did not count. Say "unknown" until you have the
  number.
