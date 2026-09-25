# Working rules for Claude in this repository

## Review before presenting — mandatory

Never report work as done, finished, ready, or fixed until it has passed an
independent review loop:

1. After implementing, spawn review/critique subagents (Agent tool) on the full
   change — at minimum separate reviewers for **security / secret leakage**,
   **backend correctness**, and **frontend / integration + docs accuracy**.
   Reviewers report only concrete, verified problems (file:line, failure
   scenario, fix), not style nits.
2. Verify every finding yourself. Fix the valid ones; dismiss wrong ones with a
   one-line reason. Re-run tests after fixing.
3. Repeat with fresh reviewers. Done means **three consecutive review rounds
   with no valid findings**. Any valid finding resets the count.
4. Only then commit/push and tell the user it is done. The report to the user
   states how many review rounds ran and what they caught.

This applies to every task: new features, fixes, and fixes made in response to
PR review bots. Do not wait to be asked.

## Project conventions

- Node house style: `docs/WRITING_V3_NODES.md` (V3 schema, tooltips on every
  input/output, `web/docs/<node_id>.md` help page, registration in
  `nodes/__init__.py` and the root `__init__.py`).
- Secrets and private addresses live only in the git-ignored `.env`
  (template: `.env.example`), read via `utils/env_manager.py`. Nothing from it
  may reach a workflow, image metadata, the browser, node outputs or logs.
- Some files use CRLF line endings (e.g. `utils/api_utils.py`); preserve them.
