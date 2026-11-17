---
name: secrets-hygiene
description: "Use when a repo, agent bundle or log may contain leaked secrets."
version: 1.0.0
author: Anne Arintseva
license: MIT
metadata:
  hermes:
    tags: [security, secrets, git, incident, rotation]
    editorial_name: Secrets hygiene
    editorial_description: Find leaked credentials without printing them, contain the leak in the right order, clean history and prevent the next one.
    requires_tools: [terminal]
    requires_toolsets: [terminal]
---

# Secrets hygiene

Use this skill when a repository, an agent bundle, a config or a log might
contain a live credential.

The order matters more than the tooling: **rotate first, clean second**. A
secret that was pushed is compromised even if the commit was deleted five
minutes later, because clones, forks, caches and CI logs already have it.

## When to use

- a scan, a review or a colleague reports a credential in a repo, a bundle or a
  log;
- an agent bundle contains `.env`, `*.pem`, `*.key` or inline tokens;
- a secret was committed and pushed, even if it was deleted afterwards;
- you are setting up prevention before the first leak.

## Hard rules

1. **Never print a secret.** Not in chat, not in a report, not in a command
   that another agent will read. Show a masked preview: first four characters
   and length.
2. **Do not paste a secret into a scanner website.** Run the check locally.
3. **Rotate before cleaning history.** Deleting the file does not un-leak it.
4. **Assume the worst scope.** If the key had admin rights, treat the whole
   account as touched until you prove otherwise.
5. **Do not commit a "cleanup" that contains the secret in the diff.**

## Step 1 — Detect

Run the bundled scanner from the repository root. It masks values by default.

```bash
python3 scripts/scan_secrets.py /path/to/repo
python3 scripts/scan_secrets.py /path/to/repo --json > /tmp/secrets.json
```

It looks for provider patterns (AWS, GitHub, Slack, Telegram bot tokens, OpenAI,
Google, Stripe, JWTs), `BEGIN PRIVATE KEY`, `SECRET=`/`TOKEN=` style assignments
and high-entropy strings.

Then check the places a file scan misses:

```bash
git log --all -p -S "password" -- . | head -200     # history, not just HEAD
git log --all --diff-filter=A --name-only -- "*.env" "*.pem" "*.key"
ls -la .env* ~/.aws ~/.ssh 2>/dev/null
```

Also look outside the repo: CI variables in plain text, docker-compose files,
Terraform state, notebook outputs, build artifacts, logs and screenshots.

## Step 2 — Classify before acting

For each hit, decide:

| Question | Consequence |
|---|---|
| Is it a real credential or a placeholder? | placeholders need no rotation, but still confuse scanners |
| Is it live? | a quick non-destructive auth call, if the provider allows one |
| What scope does it have? | read-only vs write vs admin changes the response |
| Was it pushed to a remote? | pushed = leaked, regardless of branch or deletion |
| Is it shared with other systems? | rotation breaks them unless coordinated |

Record the answer next to each finding. "Probably a test key" is a guess; prove
it or treat it as live.

## Step 3 — Contain

1. **Revoke or rotate the credential** in the provider console, in this order:
   revoke sessions/tokens derived from it, then issue a new one.
2. **Check for use.** Provider audit logs, billing spikes, new SSH keys, new
   deploy keys, new OAuth apps, changed webhooks.
3. **Invalidate caches** that could hold it: CI variables, Docker layers,
   package registries, CDN configs.
4. **Notify** whoever owns the affected system if the scope crosses teams.

Do not spend time on history rewriting before the credential is dead. The
window between "found" and "rotated" is the actual exposure.

## Step 4 — Remove from history

Only after rotation. Choose the cheapest tool that fits:

- one recent commit, not pushed: `git commit --amend` or interactive rebase;
- pushed but not merged widely: `git filter-repo --path <file> --invert-paths`;
- widespread: `git filter-repo --replace-text replacements.txt` where each line
  is `literal:OLD==>***REMOVED***` (never put the secret in a tracked file);
- then force-push, ask collaborators to re-clone, and invalidate forks you
  control.

History rewriting does not reach forks, mirrors, caches or anyone's local clone.
Say that in the report.

## Step 5 — Prevent

Add controls that fail closed:

- `.gitignore` entries for `.env`, `*.pem`, `*.key`, `secrets.*`;
- a pre-commit hook running this scanner (exit 1 blocks the commit);
- provider-side secret scanning (GitHub push protection, GitLab secret detection);
- secrets in a manager (Vault, 1Password, cloud secrets), injected at runtime;
- separate credentials per environment, short expiry, least scope;
- CI masks and forbids `echo` of secret variables;
- logs scrub tokens before they are written.

For agent bundles specifically: keep credentials out of `SKILL.md`, MCP configs
and example files, and give the agent a scoped token instead of a personal one.

## Step 6 — Report

Return:

1. **What was found** — file:line, rule, masked preview, whether it is live.
2. **Exposure** — where it was pushed, how long it was there, who could see it.
3. **Actions taken** — rotated/revoked, with timestamps.
4. **History** — what was rewritten and what remains (forks, caches, clones).
5. **Prevention** — controls added, with the exact command or config.
6. **Open questions** — unclear scopes, shared credentials, unknown consumers.

Never include the secret itself, and never include a screenshot of it.

## Pitfalls

- Deleting the file first and rotating later. That leaves a live key in every
  clone while giving a false sense of closure.
- Rotating only the key that was found, while derived tokens (sessions, refresh
  tokens, deploy keys) stay valid.
- Trusting `.gitignore` for a file that is already tracked. Ignored files stay
  tracked until removed from the index.
- Cleaning history on a shared branch without telling the team; their next push
  reintroduces the secret.
- Reporting "no secrets" after a regex pass that only covered HEAD. History and
  artifacts are where the leaks live.
