# Decisions

## D1: Treat Post-PR384 Validation As Report-Only

Decision: no product code change in this lane.

Reason: the user asked what comes next after PR #384 merged and specifically wanted the validation failure mode checked. The correct next step was to prove canonical behavior and rebuild the residual picture, not to patch DXC or WHC from stale evidence.

## D2: Preserve Exact Replay Profile

Decision: run `docling-no-write` rather than downgrade to `baseline-no-write`.

Reason: the prior JAY and WHC/EDU evidence used `docling-no-write`. A baseline replay would have produced weaker evidence and could hide the profile-specific runtime blocker.

## D3: Allow A Temporary Local Venv Pointer

Decision: create then remove an ignored local `financial-engine_v2/.venv` symlink to the existing extraction replay venv.

Reason: the fresh worktree did not have an approved in-worktree venv, but the no-write replay profile requires one. The symlink avoided dependency installation, runtime venv mutation, dependency-file changes, and global package changes.

## D4: Do Not Treat WHC/EDU Failures As Product Failures

Decision: WHC/EDU mixed-unit replay passing means expected fail-closed behavior worked.

Reason: both cases expect `failed`. The product validation gate correctly rejected unsafe accepted outputs while preserving side-effect safety.

## D5: Row Issues Need Source-Row Proof Before Code

Decision: proceed next with an exact source-row proof packet for DXC and WHC rather than a product fix.

Reason: JAY is retired, guard and WHC/EDU replays are green, but DXC and WHC row issues are still not source-proven. A row label or model output is insufficient to map a metric or scale.
