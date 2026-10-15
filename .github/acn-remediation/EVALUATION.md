# gh-aw Evaluation for ACN CVE Remediation

## Scope

This branch evaluates replacing only the SRE Agent orchestration/runtime with
GitHub Agentic Workflows.

It does not replace:

- BumpBump vulnerability interpretation;
- dependency grouping and version selection;
- dependency mutation and changeset generation;
- deterministic candidate validation;
- exact-SHA validation and merge-policy enforcement.

## Proposed architecture

```text
GitHub schedule or manual trigger
-> gh-aw Copilot engine
-> ACN remediation skill
-> approved private BumpBump candidate service/tool
-> candidate JSON
-> deterministic candidate validator/applier
-> gh-aw create-pull-request safe output
-> existing PR validation
-> separate deterministic reconciliation/auto-merge workflow
```

## What gh-aw provides

- GitHub-native schedules and events;
- skill installation;
- read-only agent execution;
- bounded bash and edit tools;
- safe PR output with repository, branch, patch-size, file-count, and draft
  restrictions;
- GitHub App credentials for safe outputs;
- compilation to auditable GitHub Actions YAML.

## Compiled prototype evidence

Validated with `gh aw` `v0.92.0` in strict mode:

- source workflow compiled with zero errors and zero warnings;
- generated actions were pinned in `.github/aw/actions-lock.json`;
- the AI `agent` job has only:
  - `contents: read`;
  - `pull-requests: read`;
  - `copilot-requests: write`;
- generated safe-output jobs isolate:
  - `contents: write`;
  - `pull-requests: write`;
- generated activation/conclusion machinery also requests `issues: write`,
  even though the evaluation workflow enables no issue-creation output.

The deterministic candidate validator has focused tests for:

- exact valid candidate acceptance;
- non-dependency path rejection;
- stale-base rejection.

All three tests pass.

## Blocking integration

BumpBump is internal AKS RP code and must not be copied into this public fork.
The production workflow needs one approved integration:

1. private remote MCP service authenticated with GitHub Actions OIDC;
2. private container/package accessible to the runner;
3. a deterministic upstream workflow that uploads candidate JSON as an
   authenticated artifact.

Until one exists, this workflow fails closed with `noop`.

## Comparison with the SRE Agent prototype

| Requirement | SRE Agent prototype | gh-aw evaluation |
| --- | --- | --- |
| Deterministic BumpBump generation | Implemented locally | External tool/service required |
| Scheduled/event execution | SRE Agent scheduler | Native GitHub Actions triggers |
| Skill/instructions | Agent instructions | Native gh-aw skill |
| GitHub PR mutation | Deterministic Python tool | Safe output |
| Exact base/path validation | Implemented | Deterministic validator included |
| ADO exact-SHA integration | Tools implemented | Custom MCP/safe-output integration required |
| Re-entry after checks | Reconciler implemented | Separate event workflow required |
| Auto-merge | Implemented and verified | Must wrap existing deterministic tool or evaluate experimental safe output |
| Platform maturity | Internal platform | GitHub public preview |

## Evaluation result so far

`gh-aw` is technically viable as the GitHub-native orchestration shell. It does
not remove the need for the deterministic remediation engine or the external
ADO lifecycle integration. The highest-priority design question is how a public
ACN workflow securely calls the internal BumpBump candidate generator without
publishing internal source or distributing broad credentials.

## Decision gate

Do not select gh-aw as the production runtime until it proves:

1. secure access to deterministic BumpBump candidate generation;
2. exact-SHA ADO correlation;
3. repeatable post-check re-entry;
4. guarded auto-merge without direct policy bypass;
5. required enterprise approval for public-preview tooling.
