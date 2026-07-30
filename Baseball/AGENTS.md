# BaseballO Repository Instructions

## Canonical repository layout

- The canonical remote is `https://github.com/CarterBeauBenson/BaseballO.git`.
- The Git repository root contains the active project in `Baseball/`.
- Do not initialize another Git repository inside `Baseball/`.

## Git workflow

- Use `dev` as the working and publishing branch.
- Never push directly to `main`.
- Never force-push, rebase published commits, or rewrite remote history without explicit user approval.
- Fetch `origin/dev` before publishing and stop for genuine conflicts or non-fast-forward divergence.
- After completing and validating requested changes, commit all in-scope changes and push them to `origin/dev` automatically.
- Authenticate through Windows Git Credential Manager. Never request, print, or store a GitHub password or token in the repository.

## Project guardrails

- The user is the ontologist. Do not modify files under `Baseball/ontology/` unless the user explicitly requests an ontology change. Report ontology gaps for the user to decide.
- Use free and open-source infrastructure. The intended pipeline stack is Apache NiFi and Apache Jena Fuseki/TDB2.
- Preserve raw source data unchanged. Derive statistics and query results downstream rather than storing them during ingestion.
- Run `python Baseball/scripts/validate_repository.py` from the repository root before committing project changes.
