# Working rules for Claude

## Review before presenting any work

Never present work as done, open or update a PR, or say "done" until the
review loop below has passed:

1. Finish the change and your own tests.
2. Spawn independent review agents (the `Agent` tool) on the full diff. Give
   each a different lens, for example:
   - correctness and edge cases, including adversarial input: huge, empty,
     malformed, deeply nested, unclosed or pathological text, and worst-case
     performance
   - integration with the host (ComfyUI frontend and backend APIs, lifecycle,
     node removal, workflow load, settings, both themes)
   - consistency between the frontend and the Python code, docs and tooltips
3. Verify every finding yourself. Fix the valid ones, then start a new round.
   Findings that are wrong get dismissed with a reason.
4. You are done only after **3 consecutive review rounds with no valid
   findings**. Any fix resets the count to zero.
5. For a PR, also subscribe to its activity (`subscribe_pr_activity`) as soon
   as it is opened, so CodeRabbit and reviewer feedback arrives without being
   asked. The PR is done only when CodeRabbit has reviewed the latest commit
   with no open findings, including the warnings in its summary comment (not
   just inline comments). If it is rate-limited, wait and then request a review
   with an `@coderabbitai review` comment.
6. When reporting back, say how many review rounds ran and what they found and
   fixed.

This applies to every task in this repository, including small fixes and
follow-ups on review comments.
