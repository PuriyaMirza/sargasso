# Progress

Status per phase from docs/PLAN.md. Statuses: not started · in progress · in review (PR open) · done (merged).

## Phase 0: setup (target Nov 30)
Status: in review (PR open on branch phase-0-setup)

Done-when checklist:
- [ ] Vercel preview deploys (the owner connects the repo to Vercel if it isn't already)
- [x] pytest passes (`cd pipeline && uv run pytest`: 1 passed)
- [x] Hook test passes (only the write aimed at .claude/ printed the "ask" JSON)
- [x] Phase 0 check findings are in docs/DECISIONS.md (levels method still OPEN)

/phase-check, 2026-11-26 (final):

| Reviewer | Check | Result | Fix |
|---|---|---|---|
| injection-guard | Config matches the owner's brief; ask rules and hook present | PASS | None. 11 files match; only the CLAUDE.md Commands section differs, as asked |
| injection-guard | Text aimed at an AI | PASS | None. The WebSearch footer is a recorded false positive |
| injection-guard | Network destinations | PASS (first run FAIL) | Removed the help.github.com template comment. Doc-only links are INFO, per the owner |
| injection-guard | Data flow, workflows, subagent reports | PASS | None |
| code-reviewer | Bugs, config, dependencies, readability | PASS (minor items) | Resize rebuilds on width only; glow measured once; comments; .gitignore entries; @types/node ^22; Next.js flags removed |
| geo-qa | Axis order, Mercator, alignment, encoding | N/A | No pipeline code until Phase 1 |
| geo-qa | Constants match DECISIONS.md; tests run | PASS | Test now checks exact bounds and dataset IDs |
| science-reviewer | No guessed thresholds; honest UNVERIFIED labels | PASS | Labelled the "clipped" note UNVERIFIED; recorded SIR's "50–100 km" |
| science-reviewer | No tons, density or forecast; footer matches PLAN.md | PASS | None. No data date until data exists (Phase 2) |
| ui-reviewer | Overflow at 390 px, contrast, footer, reduced motion, brass use, load size | PASS | None. First load about 547 KB |
| ui-reviewer | Touch targets, focus ring, map, legend, data date | N/A | Nothing interactive yet |

## Phase 1: data pipeline (target Dec 7)
Status: not started

## Phase 2: map MVP (target Dec 14)
Status: not started

## Phase 3: time and history (target Jan 4)
Status: not started

## Phase 4: coastal risk (target Jan 18, v1 live)
Status: not started

## Phase 5: polish and case study (after the trip)
Status: not started
