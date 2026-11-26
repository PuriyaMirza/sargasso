---
name: phase-check
description: End-of-phase quality gate. Runs the relevant reviewer subagents in parallel and lists what must be fixed before a PR.
---
Run the end-of-phase check for the current phase (see docs/PROGRESS.md):

1. Launch these subagents in parallel, each with a short brief of what changed in this phase:
   - injection-guard: always
   - code-reviewer: always
   - geo-qa: if pipeline/ or map layers changed
   - science-reviewer: if the levels method, labels or on-screen text changed
   - ui-reviewer: if anything visible changed
   If injection-guard reports any FAIL, stop and tell the owner before fixing anything else.
2. Combine their reports into one table: reviewer, check, PASS or FAIL, fix.
3. Fix every FAIL in the main session, then rerun only the reviewers that failed.
4. Add the final table to docs/PROGRESS.md under the current phase's heading.
