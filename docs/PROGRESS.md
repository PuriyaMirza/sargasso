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
Status: done (PR #2 merged 2026-11-27)

Done-when checklist:
- [x] One real frame committed (public/data/daily/2026-11-26.png, 191,817 bytes)
- [x] pytest covers axis order, Mercator resampling, the encoding round trip and class breaks on synthetic data (36 tests)
- [x] geo-qa passes (every one of 244,215 valid cells lands on the right PNG pixel; worst position error 3.3 km)
- [x] Measured file sizes in DECISIONS.md
- [x] Storage gate: stride 3 failed (330 KB); the owner chose stride 4 (192 KB, about 70 MB a year)
- Open: the levels method isn't confirmed, so `LEVEL_BREAKS` stays None

## Phase 2: map MVP (target Dec 14)
Status: done (PR #3 merged 2026-11-28)

Done-when checklist:
- [x] Preview works on a phone at 390 px (the owner asked to merge, 2026-11-28)
- [x] Frame lines up with coastlines at Puerto Rico, Barbados and the Yucatán (geo-qa screenshots; now also an automated test)
- [x] ui-reviewer passes (after fixes)
- [x] First load under 1 MB excluding map frames (about 710 KB compressed)

## Phase 3: time and history (target Jan 4)
Status: in progress (part 1 in review on branch phase-3-time-history: 30-day slider, monthly backfill, History view, almanac grid; part 2, the regional charts and validation, waits for the levels formula)

Done-when checklist:
- [x] 30-day slider with play
- [x] Monthly backfill, June 2016 to October 2026, with polite pacing
- [x] History view with play, and the almanac grid
- [ ] Regional sparklines (waits for the levels formula)
- [ ] Validation gate passes and is written up with screenshots. June half: passed by eye (DECISIONS.md, 2026-11-28; docs/validation/june-2025-ours.png). October-to-November half: waits for the levels formula

## Phase 4: coastal risk (target Jan 18, v1 live)
Status: not started

## Phase 5: polish and case study (after the trip)
Status: not started
