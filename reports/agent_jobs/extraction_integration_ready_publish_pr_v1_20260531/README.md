# Extraction Integration Ready Publish PR

## Summary

Publishing the clean integration branch for review as a draft PR.

## Scope

- Branch: `integrate/extraction-metric-ontology-gate-v1-20260531`
- Worktree: `/home/l4nd0/tenn-extraction-integration-ready-v1-20260531`
- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Repository: `0rl4nd0l/tenn`
- Integration commit before publish task: `687b912b74b9`
- Lane: Evaluation, supporting Financial Truth

## Pre-Publish Evidence

- Task-card validation: passed
- Registry overlap check: passed
- Registry claim: passed
- GitHub CLI installed: `gh version 2.4.0+dfsg1`
- GitHub authentication: logged in as `0rl4nd0l`
- Existing PR for head branch before publish: none
- Branch relation before publish task card commit: `0` behind / `1` ahead of `origin/migration/clean-runtime-baseline-reconstruct-v1`

## Boundaries

This publish task permits only pushing the isolated integration branch and
opening one draft PR. It does not authorize runtime startup/reload, canary
execution, document submission, backfill, DB/Qdrant/source-PDF mutation,
parser/prompt/schema changes, Cockpit UI work, model/GPU config changes, or
full-objective closure.

## Current Status

Pre-publish evidence captured. Draft PR publication is pending.
