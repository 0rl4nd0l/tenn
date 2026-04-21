# Codex Prompt — Implement Cockpit Request Standards Framework + Company Analysis Standard

You are working on Tenn, a local-first financial intelligence engine in hardening/consolidation phase.

## Lane classification
- Primary: Query Orchestration
- Secondary: Reporting
- Supporting: Provenance, Memory

## Collision rule
Before any implementation:
1. identify touched files/modules/tests
2. scan for overlap with existing request-formatting, prompt, report, or orchestration surfaces
3. classify risk:
   - LOW → safe extension
   - MEDIUM → extend only
   - HIGH → stop and output report only

If overlap risk is HIGH:
- do not implement
- output audit/report only

## Execution mode
Default to:
- AUDIT MODE first
- SAFE EXTENSION MODE only if the repo already has a natural place for this work

Do not create a parallel system if an existing standards/config/prompts/docs surface already exists.

## Goal
Create a **Cockpit request standards folder** and wire in the first standard:
- `company_analysis.md`

This is intended to create structural consistency and repeatability across a range of Cockpit request types.
Future request types are expected to include:
- daily market updates
- sector analysis
- watchlist triage
- results reaction
- news briefs

Your task is to establish the reusable structure safely, then implement/enforce the company-analysis standard in the most minimal and reversible way supported by the current repo.

## Source of truth for the company-analysis standard
Use the attached/planned markdown spec as the content source of truth.

The standard defines:
- evidence-first deep company analysis
- separation of financial truth vs narrative/context
- peer comparison
- strategy-context confer stage
- bounded skeptic pass
- missing-data recovery behavior
- final cited output structure
- confirmation-gated thesis-memory proposals

## Required outcomes

### 1. Audit existing repo surfaces first
Inspect the repo for:
- existing docs/charter/spec folders
- current cockpit prompt templates
- report/output formatting code
- orchestrator flow definitions
- request-type routing logic
- any existing analysis standards/config registries
- any current company-analysis prompt or report builder

You must identify:
- best existing location for request standards
- best existing enforcement point
- whether this should be doc-only first or doc + light runtime enforcement

### 2. Create a reusable standards folder only if safe
If the repo does not already have a natural equivalent, create a minimal additive folder for request standards with a naming scheme that can scale.

Preferred intent:
- a single place where structured request standards live
- markdown-first
- readable by humans
- future-compatible with light runtime loading or selection

Example acceptable shape only if no better existing location exists:
- `docs/cockpit_request_standards/`
or
- `financial-engine_v2/docs/cockpit_request_standards/`
or
- another existing standards/spec location already used in repo

Do not invent a second competing docs hierarchy if one already exists.

### 3. Add the first standard
Create:
- `company_analysis.md`

The file should preserve the standard sections and formatting discipline so future files can mirror it.

### 4. Add a template or README for future request standards
Create a small companion file only if useful, such as:
- `README.md`
- `_template.md`

Purpose:
- explain expected section structure
- explain how future standards should be authored
- keep formatting consistent across request types

Keep this minimal.

### 5. Implement the lightest safe enforcement path
Find the least invasive place to enforce or reference the company-analysis standard.

Safe options may include:
- loading or referencing the markdown/spec in company-analysis prompt assembly
- adding a request-type-to-standard mapping
- adding a doc path constant/config
- adding validation that company analysis uses the standard sections/order
- adding a prompt-builder hook that injects or references the standard

Do not:
- rewrite the orchestrator
- create a new agent system
- create a parallel prompt stack
- redesign company analysis runtime
- force broad architecture changes

This should be a bounded extension.

### 6. Preserve architectural boundaries
The implementation must preserve:
- deterministic financial truth boundaries
- strategy context as advisory only
- confirmation-gated thesis memory
- explicit uncertainty/missing-data handling
- no LLM-defined numeric truth

### 7. Prefer configurability over hardcoding
If there is already a request-type registry, extend it.
If there is already a prompt builder, adapt it.
If there is already a report section model, reuse it.

Avoid scattering one-off constants across many files.

## Deliverables
Provide:

### A. Audit summary
- lane
- collision assessment
- chosen execution mode
- why the chosen file locations were selected

### B. Files added/changed
List exact files.

### C. What was enforced
Be precise.
Examples:
- doc created only
- markdown standard referenced by company-analysis path
- request-type mapping added
- report-format validation added

### D. Validation
Run the smallest relevant validation only if safe:
- targeted tests
- lint
- import checks
- dry-run prompt assembly
Do not claim validation you did not run.

### E. Open risks
State what remains doc-only or unenforced.

## Strong preferences
- minimal additive changes
- one reusable standards location
- one standard file now, future-ready for others
- no duplicate systems
- no architecture expansion
- keep filenames obvious and stable

## Example future file set
Do not create all of these now unless explicitly needed, but ensure the structure can support them:
- `company_analysis.md`
- `daily_market_update.md`
- `sector_analysis.md`
- `watchlist_triage.md`
- `results_reaction.md`
- `news_brief.md`

## Hard constraints
- Do not claim system behavior is fully solved by docs alone.
- Do not over-enforce if repo surfaces are contested.
- If runtime enforcement would touch high-collision files, stop at doc creation + mapping/report.
- If no safe enforcement point exists, create the standards folder/files and output the exact recommended next enforcement point rather than forcing risky edits.

## Acceptance bar
A good result:
- creates a durable place for Cockpit request standards
- adds `company_analysis.md`
- makes future standards straightforward
- references/enforces the standard in the safest existing surface available
- avoids collisions and architecture drift
