# Data Missing

- No full Ruff lint command was run.
- No type checker was run or configured.
- GitHub Actions run history was not inspected.
- The current shell Python lacks Ruff; local tool availability was verified only
  through the existing repo venv.
- The closed PR search for `ruff lint type gate 281` returned no rows; it did
  not prove which PR or branch made the current CI/docs/dependency state
  authoritative for all target branches.
- No GitHub mutation was attempted, so #281 remains open.
