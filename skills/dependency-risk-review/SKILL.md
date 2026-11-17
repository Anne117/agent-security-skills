---
name: dependency-risk-review
description: "Use before adding or upgrading a package that will run in an agent, CI or production."
version: 1.0.0
author: Anne Arintseva
license: MIT
metadata:
  hermes:
    tags: [security, supply-chain, dependencies, npm, pypi, review]
    editorial_name: Dependency risk review
    editorial_description: Vet a package before it runs — provenance, maintainers, install scripts, typosquatting, transitive weight and known vulns — and return a verdict with evidence.
    requires_tools: [terminal]
    requires_toolsets: [terminal]
---

# Dependency risk review

Use this before a package is added, upgraded across a major version, or given a
place in an agent's toolchain. The output is a verdict with evidence, not an
opinion: **approve**, **approve with controls**, or **block**.

A package is code execution by default — via install scripts, import-time code,
or the agent calling it with attacker-influenced input.

## When to use

- a new dependency appears in a PR or a lockfile diff;
- an agent skill or MCP server is about to install a package at runtime
  (`npx -y`, `uvx`, `pip install` inside a tool);
- an incident review asks "which package introduced this";
- a security questionnaire requires an SBOM or a dependency policy.

## Step 1 — Establish identity exactly

Ambiguity here is how typosquats win. Record the exact name, scope and registry.

```bash
# npm
npm view <name> --json | jq '{name,version,license,repository,maintainers,time,scripts,dist}'

# PyPI
curl -s https://pypi.org/pypi/<name>/json | jq '{name:.info.name,version:.info.version,license:.info.license,home:.info.home_page,author:.info.author,urls:[.urls[].filename]}'

# Go
go mod download -json <module>@<version>

# Rust
cargo info <crate>@<version>
```

Check the name character by character against the real project: `reqeusts`,
`lodahs`, `python-dateutil` vs `dateutil`, scope swaps (`@company/pkg` vs
`company-pkg`), hyphen/underscore swaps. If the name is one edit away from a
popular package, treat it as hostile until proven otherwise.

## Step 2 — Provenance and maintainers

| Question | Where to look | Red flag |
|---|---|---|
| Does the repo link match the real project? | registry metadata vs project site | repo missing, or a fork with no stars |
| Who publishes it? | maintainers list, publish history | new maintainer added days before a release |
| Is publishing signed / attested? | npm provenance, sigstore, PyPI trusted publishing | no provenance for a popular package |
| When was the last release? | release history | years dormant, then a sudden release |
| How many maintainers? | registry | single account with no history |
| Is the version new? | publish timestamp | version published hours ago |

Maintainer takeover is a common real attack: the package is legitimate, the
account changed hands, and the next patch adds a payload. A recent maintainer
change plus a recent release is a block until reviewed.

## Step 3 — Install-time behaviour

Install scripts are the cheapest attack surface.

```bash
# npm: list lifecycle scripts
npm view <pkg>@<ver> scripts --json

# npm: install without scripts (recommended default for CI)
npm ci --ignore-scripts

# pip: download without installing, then unpack and read
pip download <pkg>==<ver> --no-deps -d /tmp/pkg && \
  python3 -c "import zipfile,glob;z=zipfile.ZipFile(glob.glob('/tmp/pkg/*')[0]);print('\n'.join(z.namelist()))"
```

Look for `preinstall`, `install`, `postinstall` in npm; `setup.py` with network
calls; build backends that fetch code at build time. Any download-and-execute
inside a package build is a finding, regardless of the package's popularity.

## Step 4 — Transitive weight and version ranges

```bash
npm ls <pkg> --all          # existing tree
npm view <pkg> dependencies --json
pipdeptree -p <pkg>         # if pipdeptree is available
```

- Count transitive dependencies and note any that are themselves unreviewed.
- Check the range you are adding: `^1.2.0` permits future minor releases. For
  anything security-relevant, pin exact versions and commit the lockfile.
- A new transitive dependency appearing in a lockfile diff without a direct
  change is worth a look — it may be dependency confusion.

## Step 5 — Known vulnerabilities and license

```bash
# OSV, no API key required
curl -s -X POST https://api.osv.dev/v1/query \
  -d '{"package":{"name":"<pkg>","ecosystem":"PyPI"},"version":"<ver>"}' | jq '.vulns[]? | {id,summary}'
```

Note the highest severity and whether a fixed version exists. Also record the
license and whether it is compatible with how the code will be used
(MIT/Apache-2.0 are permissive; AGPL/GPL have obligations; SSPL is not OSI).

## Step 6 — Verdict

Return a table with evidence, then one verdict.

| Check | Result | Evidence |
|---|---|---|
| Name / typosquat | pass | exact match to pypi.org/project/requests |
| Maintainers | pass | 3 maintainers, no recent additions |
| Provenance | pass | npm provenance attestation present |
| Install scripts | pass | none |
| Transitive deps | 4, all reviewed | `npm ls --all` |
| Known vulns | 0 | OSV query at 2026-11-16 |
| License | MIT | registry metadata |

**Verdicts**

- **Approve** — all checks pass; pin the exact version.
- **Approve with controls** — acceptable with specific compensating controls
  (e.g. `--ignore-scripts`, private registry proxy, run in a sandbox, review the
  diff). List each control and who owns it.
- **Block** — any of: name confusion, unexplained maintainer takeover, install
  script that fetches or executes, no upstream repository, unresolved critical
  vulnerability. Say what would change the verdict.

## Controls worth recommending

- exact pins + committed lockfile, and CI that fails on lockfile drift;
- `--ignore-scripts` for npm in CI and containers;
- a private registry proxy that mirrors and scans;
- an allowlist of approved packages for agent runtime installs;
- SBOM generation (`syft`, `cdxgen`) at build time;
- automated update PRs that a human reviews, never auto-merge for security-
  relevant packages;
- vendoring for small, stable dependencies in high-risk paths.

## Output format

1. **Target** — name@version, registry, ecosystem.
2. **Checks** — the table above with evidence and timestamps.
3. **Verdict** — one word, plus the exact controls if conditional.
4. **Residual risk** — what remains after controls.
5. **Sources** — registry URL, OSV query result, repo URL. Include the query
   time; registry data changes.

## Pitfalls

- "It's popular, so it's safe." Popular packages are the best targets and the
  best camouflage for typosquats.
- Reviewing the direct dependency and ignoring the transitive tree.
- Accepting a caret range because "semver". A compromised minor release is still
  a release.
- Reading the README instead of the package contents. The README is marketing.
- Skipping install scripts because "we install with --ignore-scripts" — check
  every place the package is installed, including agent runtime and Dockerfiles.
- Calling a package clean after one OSV query. State the time and that OSV is not
  exhaustive.
