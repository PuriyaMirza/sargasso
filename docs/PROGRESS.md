# Progress

Status per phase from docs/PLAN.md. Statuses: not started · in progress · in review (PR open) · done (merged).

## Phase 0: setup (target Nov 30)
Status: done (PR #1 merged 2026-11-27)

Done-when checklist:
- [x] Vercel preview deploys (Ready: https://sargasso-git-phase-0-setup-puriyas-projects-c08df284.vercel.app)
- [x] pytest passes (`cd pipeline && uv run pytest`: 1 passed)
- [x] Hook test passes (only the write aimed at .claude/ printed the "ask" JSON)
- [x] Phase 0 check findings are in docs/DECISIONS.md (levels method still OPEN)

## Phase 1: data pipeline (target Dec 7)
Status: in review (PR open on branch phase-1-data-pipeline)

Done-when checklist:
- [x] One real frame committed (public/data/daily/2026-11-26.png, 191,817 bytes)
- [x] pytest covers axis order, Mercator resampling, the encoding round trip and class breaks on synthetic data (36 tests)
- [x] geo-qa passes (every one of 244,215 valid cells lands on the right PNG pixel; worst position error 3.3 km)
- [x] Measured file sizes in DECISIONS.md
- [x] Storage gate: stride 3 failed (330 KB); the owner chose stride 4 (192 KB, about 70 MB a year)
- Open: the levels method isn't confirmed, so `LEVEL_BREAKS` stays None

## Phase 2: map MVP (target Dec 14)
Status: not started

## Phase 3: time and history (target Jan 4)
Status: not started

## Phase 4: coastal risk (target Jan 18, v1 live)
Status: not started

## Phase 5: polish and case study (after the trip)
Status: not started
