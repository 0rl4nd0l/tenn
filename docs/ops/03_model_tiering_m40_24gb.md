# 03 - Model Tiering Strategy (Tesla M40 24GB, 32GB RAM, SATA, i3)

Workload goal:
- Batch-first overnight financial research throughput
- Deep per-company analysis with 16k minimum context, 32k target for overnight jobs
- Semi-autonomous Level 2 reliability over raw speed

## Tier Table (A/B/C/D)

| Tier | Size Band | Quant Target | Context Policy | Primary Tasks |
|---|---|---|---|---|
| A | 7B-class | 4-bit/5-bit stable quant | Interactive: up to 8k, Overnight: up to 16k | Fast triage, summaries, control-plane prompts |
| B | 13B-class | 4-bit preferred | Interactive: 8k-12k, Overnight: 16k | Default company analysis and alert drafting |
| C | 20B-34B class (if stable) | 4-bit conservative | Interactive: capped, Overnight: 16k-32k only | Deep synthesis jobs and high-complexity reasoning |
| D | CPU-safe fallback tier | aggressive small quant | 4k-8k | Degraded-mode continuity when GPU unavailable |

Notes:
- On Maxwell + SATA, avoid frequent model churn. Keep one active batch model warm overnight.
- Treat 32k as an overnight privilege, not default interactive behavior.

## Routing Policy

### Primary Routing
1. Control/ops and low-complexity tasks -> Tier A.
2. Standard company analysis and scoring narratives -> Tier B.
3. Deep synthesis/research pack overnight -> Tier C.
4. GPU degraded/unavailable -> Tier D.

### Upgrade Rules
- Promote from A -> B if task requires multi-document synthesis or richer reasoning.
- Promote from B -> C only when:
  - overnight window
  - queue pressure low
  - memory headroom verified

### Downgrade Rules
Downgrade one tier when any occurs:
- OOM/KV pressure event
- repeated slow token throughput below SLO threshold
- queue backlog exceeds policy threshold

### Retry Rules
- First retry: same tier with reduced context budget.
- Second retry: downgrade tier and rerun.
- Third retry: mark partial/deferred and move to overnight queue.

## Memory Policy (Long Context + KV Risk)

### Interactive Window
- Hard cap context lower than overnight (target 8k-12k).
- Keep concurrency conservative to avoid fragmentation.
- Prefer excerpted evidence over full-corpus payloads.

### Overnight Window
- Allow 16k baseline and 32k only for deep synthesis queue.
- Use strict queue serialization for largest-context jobs.
- Avoid simultaneous model swaps while long-context jobs run.

### Fragmentation and Stability Handling
- Minimize tier switching during active windows.
- Use periodic idle windows for model unload/reload hygiene.
- Trigger downgrade automatically on repeated allocation failures.

## Optional Cloud Fallback Policy (Explicit Opt-in)

Cloud fallback allowed only when all local conditions fail:
- Tier downgrade chain exhausted
- context requirement cannot be met locally within SLA
- job is marked business-critical

Governance gates:
- explicit operator approval or policy flag
- provenance records include `execution_location=cloud`
- rerun locally when capacity recovers if reproducibility policy requires

## Batch-First Defaults
- Default overnight tier: B
- Deep overnight pack: C on dedicated queue
- Interactive default: A/B with context cap
- D only for resilience mode
