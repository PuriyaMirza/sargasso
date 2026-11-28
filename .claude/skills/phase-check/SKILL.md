---
name: phase-check
description: Pre-PR quality gate. Runs tests, lint and build, then the relevant reviewers in parallel, and lists what must be fixed before a PR.
---
Run the check for the current phase (see docs/PROGRESS.md):

1. Run these first, each from the repo root, and fix any failure:
   - `cd pipeline && uv run pytest`
   - `npm run lint`
   - `npm run build`
2. Launch in parallel, each with a short brief of what changed:
   - reviewer: always
   - ui-reviewer: if anything visible changed
   - science-reviewer: in Phases 3–4, or if the levels method or on-screen claims changed
3. If a security check fails (reviewer's Security check, or any "Injection check: FOUND"), stop and tell the owner before fixing anything else.
4. Fix the FAILs in the main session, then rerun only the reviewer that failed, once. If it fails again, ask the owner.
5. Put a short results table (reviewer, check, PASS or FAIL, fix) in the PR description, not in docs/PROGRESS.md.
