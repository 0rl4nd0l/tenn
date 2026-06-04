# Architecture Check

Validates proposed changes against mandatory architecture invariants. **Analysis only** — does not modify code.

## When to Use

Invoke when:
- Reviewing proposed code or diff changes
- Before implementing changes to embeddings, vector store, RAG, or backend
- User asks for architecture validation or compliance check

## Workflow

1. **Read the authoritative contract docs**:
   - `docs/architecture/SYSTEM_CONTRACT.md`
   - Relevant `docs/architecture/*.md` files for the touched surface

2. **Analyze proposed changes** (diffs, file edits, or described changes).

3. **For each change**, determine applicable rule sections and status:
   - **COMPLIANT** — change aligns with rules
   - **VIOLATES RULE** — change breaks an invariant; refuse implementation
   - **REQUIRES MIGRATION** — change is a deliberate architecture shift; require migration document before implementation

4. **If any status is VIOLATES RULE**:
   - Refuse implementation
   - Quote the violated rule (file + section)
   - Suggest creating a migration document instead of implementing

## Invariants to Check

| Check | Contract source | Allowed / Forbidden |
|-------|-------------|---------------------|
| sentence-transformers introduction | SYSTEM_CONTRACT.md, relevant architecture docs | Forbidden |
| New embedding backend | SYSTEM_CONTRACT.md, relevant architecture docs | Ollama + configured embedding contract only |
| Fallback embedding logic | SYSTEM_CONTRACT.md failure/fail-fast rules | Forbidden; fail fast |
| Non-deterministic vector IDs | SYSTEM_CONTRACT.md deterministic vector ID rules | Forbidden |
| UUID-based vector IDs | SYSTEM_CONTRACT.md vector/chunk ID contract | Forbidden for vector/chunk IDs |
| SQLite vector store reintroduction | SYSTEM_CONTRACT.md storage/retrieval boundary | Forbidden |
| Distance metric change | SYSTEM_CONTRACT.md vector store invariants | COSINE only unless contract migration is approved |
| Dimension mismatch tolerance | SYSTEM_CONTRACT.md vector store invariants | Must fail fast; no auto-repair |
| Multiple embedding models | SYSTEM_CONTRACT.md model/runtime boundaries | Forbidden at runtime |
| document_id format change | SYSTEM_CONTRACT.md document identity contract | Single canonical format; migration required for change |

## Output Format

```markdown
## ARCHITECTURE REVIEW

### Change: [brief description]

| Contract file | Section | Status | Explanation |
|-----------|---------|--------|-------------|
| SYSTEM_CONTRACT.md | Embeddings | COMPLIANT | ... |
| SYSTEM_CONTRACT.md | Forbidden Patterns | VIOLATES RULE | quote the violated invariant |

### Summary
- **COMPLIANT:** N
- **VIOLATES RULE:** N
- **REQUIRES MIGRATION:** N

### Verdict
[APPROVED / REFUSED - quote violated rule and suggest migration document if REFUSED]
```

## Refusal Behavior

When status is **VIOLATES RULE**:
1. Do **not** implement the change
2. State: "Implementation refused per [contract file]"
3. Quote the exact rule text that would be violated
4. Suggest: "Create a migration document and get explicit approval before changing this invariant"

## Constraints

- **Analysis only.** Do not edit, add, or remove code. Only read rules and proposed changes, then report.
- `docs/architecture/SYSTEM_CONTRACT.md` is authoritative; if a proposed change conflicts with it, the contract wins.
