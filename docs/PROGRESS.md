# Progress

Status per phase from docs/PLAN.md. Statuses: not started · in progress · in review (PR open) · done (merged).

## Phase 0: setup (target Nov 30)
Status: done (PR #1 merged 2026-11-27)

Done-when checklist:
- [x] Vercel preview deploys (Ready: https://sargasso-git-phase-0-setup-puriyas-projects-c08df284.vercel.app)
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
Status: in review (PR open on branch phase-1-data-pipeline)

Done-when checklist:
- [x] One real frame committed (public/data/daily/2026-11-26.png, 191,817 bytes)
- [x] pytest covers axis order, Mercator resampling, the encoding round trip and class breaks on synthetic data (36 tests)
- [x] geo-qa passes (every one of 244,215 valid cells lands on the right PNG pixel; worst position error 3.3 km)
- [x] Measured file sizes in DECISIONS.md
- [x] Storage gate: stride 3 failed (330 KB); the owner chose stride 4 (192 KB, about 70 MB a year)
- Open: the levels method isn't confirmed, so `LEVEL_BREAKS` stays None

/phase-check, 2026-11-27 (final; ui-reviewer skipped because nothing visible changed):

| Reviewer | Check | Result | Fix |
|---|---|---|---|
| injection-guard | Config changes explained; security lines intact | PASS | None. Workflow is the Phase 1 job; CLAUDE.md change is the owner's request, with every Security line kept |
| injection-guard | Text aimed at an AI, network hosts, data flow, workflow, subagent reports | PASS | None. The stray `.nonexistent` was never committed |
| code-reviewer | Failure handling | PASS (after fixes) | A bad or empty frame now tries the mirror; frame date checked; old frames deleted only after latest.json is updated; atomic cache writes; a note when the mirror has nothing newer |
| code-reviewer | Workflow | PASS (after fix) | The job runs only on main |
| code-reviewer | Readability, unused code | PASS (after fixes) | Comments on test-only and Phase 3 helpers; duplicate function name renamed |
| geo-qa | Axis order, Mercator rows, corners, encoding, tests | PASS | Added a test that latest.json's corners and size match the PNG |
| geo-qa | Alignment (no land layer until Phase 2) | PASS | Independent check: inland Puerto Rico, Barbados and the Yucatán are no data |
| science-reviewer | No guessed thresholds; honest encoding range | PASS | Recorded that the data are clipped at -0.002 and 0.004 |
| science-reviewer | No tons, density or forecast; 7-day label | PASS | Recorded the SaWS labelling and the coastal-mask clues as UNVERIFIED |

## Phase 2: map MVP (target Dec 14)
Status: not started

## Phase 3: time and history (target Jan 4)
Status: not started

## Phase 4: coastal risk (target Jan 18, v1 live)
Status: not started

## Phase 5: polish and case study (after the trip)
Status: not started
