# Architecture Check

Validates proposed changes against mandatory architecture invariants. **Analysis only** — does not modify code.

## When to Use

Invoke when:
- Reviewing proposed code or diff changes
- Before implementing changes to embeddings, vector store, RAG, or backend
- User asks for architecture validation or compliance check

## Workflow

1. **Read rule files** in `.cursor/rules/`:
   - `00_mandatory_index.md`
   - `backend_architecture.md`
   - `embedding_rules.md`
   - `vector_store_invariants.md`
   - `failure_policy.md`

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

| Check | Rule source | Allowed / Forbidden |
|-------|-------------|---------------------|
| sentence-transformers introduction | backend_architecture.md, embedding_rules.md | Forbidden |
| New embedding backend | backend_architecture.md, embedding_rules.md | Ollama + nomic-embed-text only |
| Fallback embedding logic | backend_architecture.md, embedding_rules.md, failure_policy.md | Forbidden; fail fast |
| Non-deterministic vector IDs | backend_architecture.md, vector_store_invariants.md | Forbidden |
| UUID-based vector IDs | backend_architecture.md (UUID Usage Policy) | Forbidden for vector/chunk IDs |
| SQLite vector store reintroduction | backend_architecture.md (SQLite) | Forbidden |
| Distance metric change | backend_architecture.md, vector_store_invariants.md | COSINE only |
| Dimension mismatch tolerance | backend_architecture.md, vector_store_invariants.md | Must fail fast; no auto-repair |
| Multiple embedding models | embedding_rules.md | Forbidden at runtime |
| document_id format change | backend_architecture.md (Document ID Contract) | Single canonical UUID format; migration required for change |

## Output Format

```markdown
## ARCHITECTURE REVIEW

### Change: [brief description]

| Rule file | Section | Status | Explanation |
|-----------|---------|--------|-------------|
| backend_architecture.md | Embeddings | COMPLIANT | ... |
| embedding_rules.md | Forbidden | VIOLATES RULE | sentence-transformers is forbidden; quote: "..." |

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
2. State: "Implementation refused per [rule file]"
3. Quote the exact rule text that would be violated
4. Suggest: "Create a migration document and get explicit approval before changing this invariant"

## Constraints

- **Analysis only.** Do not edit, add, or remove code. Only read rules and proposed changes, then report.
- Rule files are authoritative; if a proposed change conflicts with them, the rule wins.
