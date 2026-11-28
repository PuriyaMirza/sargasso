# Decisions

Newest last. Each entry: date, decision, why, source. UNVERIFIED marks anything not confirmed from a primary source.

## 2026-11-26: Plan, approval gate and subagents
- Decision: Adopt docs/PLAN.md, CLAUDE.md and the .claude/ config (ask rules, Bash guard hook, six subagents, /phase-check skill) as written by the owner.
- Why: Keeps work phase by phase, and makes any edit to agent config or workflows need the owner's explicit approval, which limits what a prompt injection could change.
- Source: Owner's Phase 0 brief.

## 2026-11-26: Main data source and axis facts (Phase 0 check 1)
- Decision: Use `noaa_aoml_atlantic_oceanwatch_AFAI_7D` on cwcgom.aoml.noaa.gov. Read variable `AFAI` with dimensions (time, latitude, longitude) and treat NaN as no data. Read axis values from the file instead of computing them, because latitude spacing is 0.015001974°, not exactly 0.015°.
- Why: Confirmed on 2026-11-26. All three IDs (`_1D`, `_3D`, `_7D`) exist. Latitude ascends from 0 to 38 (2534 values). Longitude ascends from -98 to -38 (4001 values, 0.015°). Times are at 12:00Z, in seconds since 1970-01-01. The latest time was 2026-11-25T12:00:00Z on all three. `actual_range` is -0.002 to 0.004, `_FillValue` is NaN, and there is no units attribute (the summary says "reflectance units").
- Source: https://cwcgom.aoml.noaa.gov/erddap/info/noaa_aoml_atlantic_oceanwatch_AFAI_7D/index.csv · latest time: `curl -g "https://cwcgom.aoml.noaa.gov/erddap/griddap/noaa_aoml_atlantic_oceanwatch_AFAI_7D.csv?time[last]"`

## 2026-11-26: The time axis has gaps
- Decision: The pipeline uses the time values ERDDAP lists and never assumes one frame per day. A missing day is a gap, never zeros.
- Why: The 1D dataset is missing 252 days since 2016-06-18, including a 185-day gap starting 2016-08-03. Time counts: 1D 3561, 3D 3561, 7D 3560.
- Source: https://cwcgom.aoml.noaa.gov/erddap/info/noaa_aoml_atlantic_oceanwatch_AFAI_1D/index.csv

## 2026-11-26: Time of day new data appears: UNVERIFIED
- Decision: In Phase 1, make the daily job safe to re-run: it does nothing if `time[last]` hasn't changed. Each run logs `time[last]`, and we pick the schedule from that log.
- Why: `Last-Modified` headers are generated per request, so they show nothing, and no published schedule was found.
- Source: `curl -g -sI "https://cwcgom.aoml.noaa.gov/erddap/griddap/noaa_aoml_atlantic_oceanwatch_AFAI_7D.csv?time[last]"`

## 2026-11-26: Download size of one full-region 7-day frame
- Decision: Note these as download costs. The Phase 1 storage gate (300 KB) applies to the PNG we commit, not to these NetCDF downloads.
- Why: Measured for the latest frame: stride 3 = 4,531,792 bytes (about 845 × 1334 cells); stride 6 = 1,142,724 bytes (about 423 × 667 cells). The server sent no Content-Length, so the files were downloaded and deleted.
- Source: https://cwcgom.aoml.noaa.gov/erddap/griddap/noaa_aoml_atlantic_oceanwatch_AFAI_7D.nc?AFAI[(last)][(0.0):3:(38.0)][(-98.0):3:(-38.0)] (and `:6:` for stride 6)

## 2026-11-26: Fallback mirror (Phase 0 check 2)
- Decision: The fallback is upwell.pfeg.noaa.gov, dataset `noaa_aoml_ae10_d11a_85ab` ("7-day cumulative USF AFAI Fields"). Its ID differs from the primary's, so the code stores a dataset ID per server.
- Why: It has the same variable, NaN fill value, grid, axis order, time range and latest time (2026-11-25T12:00Z). A 15 × 15 sample near 16N, 60W for 2026-11-25 was byte-identical on both servers. The mirror also has 1D (`noaa_aoml_9406_b52e_b95b`) and 3D (`noaa_aoml_3896_1b40_b974`) datasets; their values weren't compared (UNVERIFIED).
- Source: https://upwell.pfeg.noaa.gov/erddap/info/noaa_aoml_ae10_d11a_85ab/index.csv

## 2026-11-26: Levels method: OPEN, no class breaks chosen (Phase 0 check 3)
- Decision: No class breaks yet. Phase 1 can fetch and encode the AFAI index, but must not classify it until a primary source confirms the method.
- Why: The plan forbids guessed thresholds, and the key papers couldn't be read from this environment. Findings so far:
  - ERDDAP metadata: AFAI is "in reflectance units" and saturates under sun glint, clouds or thick aerosols. It cites Hu et al. 2015, Remote Sensing of Environment 167:229–246, doi:10.1016/j.rse.2015.05.022. It doesn't say whether values are background-subtracted.
  - Wang and Hu 2016, Remote Sensing of Environment 183:350–367, doi:10.1016/j.rse.2016.04.019 (UNVERIFIED, search snippets only): detection threshold 1.79e-4 (AFAI above background); AFAI -8.77e-4 = 0% coverage and 4.41e-2 = 100% coverage, with a linear mapping between them. These numbers are for MODIS. The paper's record is at https://pure.lib.usf.edu/en/publications/mapping-and-quantifying-emsargassumem-distribution-and-coverage-i-2/, but it doesn't show these values. Note that ERDDAP's `actual_range` tops out at 0.004, far below the 100% value, so the ERDDAP values may be clipped (UNVERIFIED, because it rests on the unverified 100% value). Check this in Phase 1.
  - USF SaWS: describes a density product with a color scale of 0.00–0.10 ‰ (per mille), but gives no conversion steps. https://optics.marine.usf.edu/projects/saws.html
  - NOAA SIR: risk classes low, warning, medium and high against a multi-day baseline. The page says "the algorithm examines these data in the surrounding 50–100 km" and gives no numeric thresholds or baseline length. The "50 km" and the 0.001 and 0.003 thresholds in docs/PLAN.md were not found on the page (confirmed by the data-scout and science-reviewer). Settle this before Phase 4. https://cwcgom.aoml.noaa.gov/SIR/
  - Blocked: doi.org, www.sciencedirect.com, repository.library.noaa.gov and science.whoi.edu (DNS failure); sargcoop.org and digitalcommons.usf.edu (network proxy 403).
- Next: The owner shares the Wang and Hu 2016 PDF, or allows one of the blocked hosts, so data-scout can read the primary source.
- Source: https://cwcgom.aoml.noaa.gov/erddap/info/noaa_aoml_atlantic_oceanwatch_AFAI_7D/index.html

## 2026-11-26: Injection check: false positive
- Decision: Treat the two "Injection check: FOUND" reports from the Phase 0 scouts as a false positive. The owner reviewed this and said to continue.
- Why: The flagged text, "REMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.", is a footer the WebSearch tool adds to every search result, not text from a web page. A control search on an unrelated query ("ERDDAP griddap documentation") returned the same line, and WebSearch's own tool description asks for a Sources list. It only asks for citations: no file edits, new hosts or approval bypass.
- Source: Control search in the main session, 2026-11-26.

## 2026-11-26: Phase 0 scouts ran without data-scout's tool limits
- Decision: Note it; no change. Agent files load at session start, so `data-scout` wasn't available when the checks ran. The checks used general-purpose agents on the haiku model, with data-scout's instructions included word for word.
- Why: General-purpose agents can use every tool, so the tool list wasn't enforced. One scout called a read-only documentation tool outside data-scout's list (it changed nothing) and left a scratch file at /tmp/scratch_afai_info.html. From the next session on, the real data-scout loads with its tool list.
- Source: Scout reports, 2026-11-26.

## 2026-11-26: injection-guard first run: config matches the owner's brief; one strict FAIL resolved
- Decision: Accept. injection-guard pulled the owner's brief from the session transcript and diffed it against the commit. All 11 files match, except the Commands section of CLAUDE.md, which the owner asked to be filled in. The hook is executable. Check 3 (network destinations) failed on a strict reading: three hosts outside its list appear as text only (optics.marine.usf.edu and dm3.caricoos.org in docs, help.github.com in a template comment in .gitignore). The owner said to continue. The .gitignore comment was removed. optics.marine.usf.edu stays a validation link that code never fetches.
- Why: Check 3 is meant for hosts that code, scripts or workflows contact. No code contacts these.
- Source: injection-guard report, 2026-11-26.

## 2026-11-26: Next.js config left at defaults
- Decision: Remove `cacheComponents` and `partialPrefetching`, which create-next-app 16.4.6 turned on.
- Why: The site is static (the browser reads files from public/data), so it doesn't need them. With them on, later pages could fail to build unless dynamic data sits inside Suspense, which adds complexity a beginner doesn't need.
- Source: code-reviewer, 2026-11-26.

## 2026-11-27: CLAUDE.md: more room for judgment, same security rules
- Decision: At the owner's request, loosen the process rules: merging is allowed when the owner asks in chat; small plan deviations are allowed if logged here; well-maintained open-source dependencies may be added without asking (listed in the PR); small fixes to earlier phases are allowed; a growing task continues if it stays within the phase's goal; quick single-page lookups are allowed in the main session; the WebSearch footer is named as known boilerplate. All security rules stay as they were.
- Why: Phase 0 and early Phase 1 stopped several times on process rules (merging, dependencies, the WebSearch footer) where the owner's answer was always to continue.
- Source: Owner's request in chat, 2026-11-27.

## 2026-11-27: Python libraries for the pipeline
- Decision: numpy, netCDF4 and Pillow, chosen by the owner. They run only in the daily GitHub job; nothing reaches visitors' browsers.
- Why: These are the standard tools for reading NOAA's NetCDF files and writing PNGs, so there's less code of our own to maintain. Measured install size: 114 MB on the runner.
- Source: Owner's answer, 2026-11-27.

## 2026-11-27: Storage gate: daily frames at stride 4 (about 6.7 km), not stride 3
- Decision: Take every 4th data cell for the daily map, chosen by the owner. docs/PLAN.md is updated.
- Why: Measured on the 2026-11-26 frame:

  | Option | Daily file | Repo growth per year |
  |---|---|---|
  | Stride 3 PNG (5 km), as planned | 329,948 bytes | about 120 MB (fails both gates) |
  | Stride 3, lossless WebP | 297,004 bytes | about 108 MB (fails growth) |
  | Stride 3, WebP at half precision | 251,194 bytes | about 92 MB (thin margin) |
  | **Stride 4 PNG (6.7 km)** | **191,817 bytes** | **about 70 MB** |

  Deleting frames after 30 days doesn't shrink git history, so growth is 365 frames a year. File size rises on less cloudy weeks: 38.5% of pixels had data on this frame. The NetCDF download at stride 4 is 2,557,104 bytes.
- Source: Local measurements, 2026-11-27; owner's answer.

## 2026-11-27: Data PNG encoding
- Decision: PNG value 0 = no data (NaN: cloud, land, outside the product's coverage). Values 1–255 = AFAI scaled linearly from -0.002 to 0.004, clipped at both ends. One step = 2.36e-5 AFAI. The range is the dataset's own `actual_range`, not a threshold. latest.json carries the scale so the browser can decode it.
- Why: 8-bit grayscale PNGs are small, lossless and easy for the browser to color with a lookup table. The round trip is tested to within half a step.
- Source: https://cwcgom.aoml.noaa.gov/erddap/info/noaa_aoml_atlantic_oceanwatch_AFAI_7D/index.csv (actual_range)

## 2026-11-27: Web Mercator resampling
- Decision: Each output row copies the nearest data row (no blending). The number of rows is chosen so each output row is no taller than the shortest data row in Mercator, which sits at the equator, so no data row is ever skipped. At stride 4, 634 data rows become 687 image rows. Corners are the outer cell edges (exact values in latest.json).
- Why: MapLibre stretches an image evenly between its corners in Web Mercator. Copying the nearest row keeps no-data pixels as no data and never invents values. The largest shift this causes is half an image row, about 3 km.
- Source: pipeline/src/sargasso_pipeline/grid.py and pipeline/tests/test_grid.py.

## 2026-11-27: What the 7-day timestamp means: UNVERIFIED
- Decision: Label frames "7-day composite dated YYYY-MM-DD", using ERDDAP's timestamp, without claiming which seven days it covers.
- Why: The metadata says only "7-day cumulative" and "Reference Time". A small sample (16N, 60W) didn't match "that day plus the six before" as a mean or a max, so the window is unknown.
- Source: https://cwcgom.aoml.noaa.gov/erddap/info/noaa_aoml_atlantic_oceanwatch_AFAI_7D/index.csv ; https://optics.marine.usf.edu/projects/SaWS/README.pdf

## 2026-11-27: Daily schedule
- Decision: Run at 01:23 and 13:23 UTC, plus a manual "Run workflow" button. A run with no new frame changes nothing.
- Why: One observation: the 2026-11-26 frame appeared between about 22:10 UTC on Nov 26 and 00:21 UTC on Nov 27. The midday run is a backup. Revisit after a week of run logs; each run prints the newest frame's time.
- Source: Phase 0 scout (22:10 UTC) and the first pipeline run (00:21 UTC).

## 2026-11-27: Coverage and coastal edges in the real data
- Decision: Note for the levels method and for Phase 2's no-data hatch.
- Why: USF's product covers only a few rectangular boxes within 0–38N, 98–38W; everything else is NaN. Five inland points (Florida, the Yucatán, Puerto Rico, Cuba, Venezuela) are NaN, so land is already no data. Values are high right along many coastlines (Cuba, Hispaniola, the Yucatán, Venezuela). That's likely shallow seafloor or murky water rather than sargassum, so the levels method needs to deal with near-shore pixels.
- Source: Frame 2026-11-26, checked locally.

## 2026-11-27: Levels method: still OPEN after a second search
- Decision: Keep `LEVEL_BREAKS = None`. latest.json says the levels are pending, and the map will show the continuous relative index until a source is confirmed.
- Why: The only primary source reached was USF's SaWS README. It says the most useful image is "FA_UNET_DENSITY", a "Sargassum density map for the past 7 days" with a "% cover" scale from 0.00 to over 0.4, but it gives no class breaks, and that's a different product from ERDDAP's AFAI. Wang and Hu 2016 remains unreachable. Newly blocked: api.semanticscholar.org and pure.lib.usf.edu (proxy 403); www.mdpi.com and arxiv.org (DNS); three PDFs on optics.marine.usf.edu (HTTP 401).
- Source: https://optics.marine.usf.edu/projects/SaWS/README.pdf (pages 2–3)

## 2026-11-27: GitHub Action pinned to a commit; no third-party setup actions
- Decision: The only action used is actions/checkout, pinned to v7.0.1 (commit 3d3c42e5aac5ba805825da76410c181273ba90b1, released 2026-07-17). uv is installed from PyPI at a pinned version (`pipx install uv==0.11.32`). Permissions are empty by default, and `contents: write` is granted only to the data job.
- Why: Fewer outside actions mean less supply-chain risk (pinned SHAs and minimal permissions, as the security rules ask).
- Source: `git ls-remote --tags https://github.com/actions/checkout`

## 2026-11-27: A data-scout saved a web page into the repo
- Decision: Moved it out without committing it, and noted it here. No other change.
- Why: While searching for the method, data-scout saved USF's SaWS page (196 KB of HTML) as `.nonexistent` at the repo root, even though its instructions say read-only. Its Bash tool can write files, so "read-only" is only an instruction. The main session scanned the file and found no text aimed at an AI, no invisible characters and no encoded strings; its HTML comments are developer notes. The copy is kept in the session scratchpad for injection-guard.
- Source: Main session, 2026-11-27.

## 2026-11-27: ERDDAP's AFAI is clipped at both ends (closes the Phase 0 question)
- Decision: Treat -0.002 as "-0.002 or less" and 0.004 as "0.004 or more". The encoding already does this: code 1 is the floor, code 255 the ceiling.
- Why: In the 2026-11-26 frame (244,215 valid cells), 11.37% of values sit exactly at -0.002 and 0.25% exactly at 0.004, with nothing beyond. That pile-up means the producer clips the values. So the Wang and Hu 100% coverage value (4.41e-2, UNVERIFIED) can't be reached in this product, and any coverage conversion must allow for the ceiling.
- Source: Frame 2026-11-26, checked locally (pipeline/.cache).

## 2026-11-27: What happens when a frame is bad
- Decision: A frame that can't be read, has no data at all, or has the wrong date counts as a failure for that server, and the mirror is tried next. If both fail, the job stops with an error and the site keeps the last good frame. It doesn't fall back to an older date, because that would hide the problem. The job doesn't reject frames that are mostly cloud: coverage varies a lot from week to week, and any cut-off would be a guess. Instead, latest.json records `data_fraction` (the share of pixels with data, 0.377 on 2026-11-26) so the map can show it.
- Why: Failures stay loud (a red Action and an email to the owner) without ever showing a broken frame.
- Source: code-reviewer, 2026-11-27.

## 2026-11-27: More context from science-reviewer (all UNVERIFIED unless quoted)
- SaWS weekly images are labelled by their last day: the README shows "3/10/2023 - 3/16/2023 - 7DAY FA_UNET_DENSITY" under "Composite DOY 075" (day 75 = March 16). That's a different product from ERDDAP's AFAI_7D, and the 16N, 60W sample didn't fit, so the ERDDAP window stays UNVERIFIED. https://optics.marine.usf.edu/projects/SaWS/README.pdf
- Search snippets (not a primary source) say USF's operational products mask "coastal waters 0–30 km from the shore" because of shallow bottoms, suspended sediment and mixed land–water pixels, citing Hu et al. 2016 and Wang and Hu 2020. That matches the bright coastal edges in our frame. Confirm it before using it in the levels method.
- For the Phase 3 validation: the SaWS page says "we have applied a wider color stretch after January 2025", so bulletin images from before and after that month aren't directly comparable. https://optics.marine.usf.edu/projects/SaWS.html
- Source: science-reviewer, 2026-11-27.

## 2026-11-27: Land layer from Natural Earth 1:10m, clipped once
- Decision: `npm run land` makes public/data/land.geojson from the world-atlas 2.0.2 package (Natural Earth 1:10m land). It clips to 100–36W, 2S–40N (a little beyond the data, so panning edges still show land), simplifies to 30% of the points (keeping every island), and rounds to 0.001° (about 110 m). Result: 153,570 bytes, or 48,456 compressed.
- Why: The full-detail clip is 498 KB. At 30%, coastline detail stays far finer than the 6.7 km data pixels, and Barbados, Grand Cayman and Puerto Rico all survive. world-atlas and mapshaper are dev-only tools; nothing from them ships except the GeoJSON.
- Source: https://github.com/topojson/world-atlas (Natural Earth, public domain)

## 2026-11-27: MapLibre 6.17.0, with its worker served from /maplibre/
- Decision: Pin maplibre-gl 6.17.0 (released 2026-11-07; newer versions came out within the last two weeks). Before each build, `scripts/copy-maplibre-worker.mjs` copies MapLibre's web worker into public/maplibre/ (gitignored), and the map calls `setWorkerUrl()` to point at it. The map uses no outside tiles or fonts: just a background, the frame and the land layer, so it contacts no new hosts.
- Why: MapLibre 6 looks for its worker next to its own file, and that file moves when Next.js bundles it.
- Source: node_modules/maplibre-gl/dist (the worker URL logic in maplibre-gl.mjs)

## 2026-11-27: How the map colors the frame
- Decision: The browser reads the PNG's exact values (color management off), colors them with a 256-entry lookup table and hands MapLibre the colored copy. The scale is a continuous stretch over the data's own range, -0.002 to 0.004: near ink up to 30%, then dim stone (55%), brass (80%) and bright gold (100%). No data is transparent, so a faint paper hatch on the map's ground shows through; land draws on top of everything except the coastline.
- Why: Calm ocean should look like the ink ground (docs/PLAN.md), and only higher values should stand out. Each stop is lighter than the one before (tested), so the scale reads in grayscale. These are display stops, not level classes; the legend says the levels are pending.
- Source: lib/frame.ts, app/sargassum-map.tsx

## 2026-11-27: Reading the data at build time; map view in the address
- Decision: The page reads latest.json when Vercel builds it, so the data date is in the HTML before any JavaScript runs. The daily data commit triggers a rebuild. The map keeps its view in the address (`#map=zoom/lat/lng`), so views can be shared and screenshotted.
- Why: Faster first paint and a date that's always visible. MapLibre's built-in hash option needs no extra code.
- Source: app/page.tsx

## 2026-11-27: Phase 2 first-load size
- Decision: Accept. Measured compressed transfer on the production build (`next start`): page, scripts, CSS and fonts 375 KB; land 48 KB; MapLibre worker 148 KB; about 710 KB in all, excluding the 187 KB map frame. Under the 1 MB budget. Vercel serves Brotli, which is usually smaller still.
- Source: Playwright and curl against `next start`, 2026-11-27.

## 2026-11-27: mapshaper runs on demand, not as a dependency
- Decision: Remove mapshaper from devDependencies; `npm run land` runs the pinned version through `npx --yes mapshaper@0.7.101`.
- Why: mapshaper pulls in better-sqlite3 and msgpackr-extract, which run install scripts (native builds, possibly downloading prebuilt files from GitHub). As a dependency, those would run on every `npm install` and every Vercel build, for a tool we use once. The lockfile now has no packages with install scripts.
- Source: injection-guard noted two install-script packages; `npm ls better-sqlite3` traced them to mapshaper.

## 2026-11-27: Wording that doesn't overclaim
- Decision: The header says "A relative index of floating sargassum…" instead of "Where sargassum is this week". The readout shows the marker on the color scale and the AFAI value, with no 0–100 number. The coastal note says bright near-shore pixels "may be" shallow seafloor, sediment or mixed land–water pixels, and that "this map can't yet tell them apart". The coverage line says "N% of the frame has data in this composite; the rest is cloud, land or outside coverage."
- Why: A 0–100 number reads like percent cover, and the bottom of the scale isn't "no sargassum". The 7-day window is unverified. The coastal artifact is likely but not confirmed from a primary source. data_fraction counts frame pixels, not sargassum.
- Source: science-reviewer, 2026-11-27.

## 2026-11-27: Alignment test against the land layer
- Decision: pipeline/tests/test_alignment.py draws land.geojson onto the committed PNG's grid and checks that (a) pixels fully inside land almost never hold data (at most 0.5%), and (b) shifting the frame 3 pixels in any direction puts clearly more data on land. The daily job runs it before each update.
- Why: It protects the Puerto Rico, Barbados and Yucatán alignment check automatically. The 249 "data on land" pixels found on 2026-11-26 (0.16%) are lakes and reservoirs that Natural Earth's land layer doesn't cut out: Okeechobee, Pontchartrain, Kentucky Lake, Kerr Lake, Izabal, Guri and Brokopondo. Every shift, even one pixel, makes the overlap worse, so the frame sits within a pixel of the coastline.
- Source: geo-qa, 2026-11-27.
## 2026-11-27: Review process trimmed (owner's option A)
- Decision: One `reviewer` agent (sonnet) replaces code-reviewer, geo-qa and injection-guard. science-reviewer moves to sonnet and runs only in Phases 3–4 or when the method or on-screen claims change. ui-reviewer is unchanged. data-scout is removed; research happens in the main session under the same injection rule. /phase-check runs pytest, lint and build first, reruns a failed reviewer once, and puts its table in the PR instead of PROGRESS.md. docs/PLAN.md now uses the new names. reviewer also checks that the approval lock (settings.json ask rules and hook) is intact, and that map frames line up with coastlines.
- Why: Reviews took too long on every PR. The reviewers overlapped (code-reviewer and injection-guard both checked Actions pinning, permissions and secrets). data-scout's read-only rule wasn't enforced: its Bash tool could write files, and it did (see "A data-scout saved a web page into the repo").
- Source: Owner's request in chat, 2026-11-27.

## 2026-11-28: reviewer's invisible-Unicode scan now runs
- Decision: reviewer.md gives the exact scan command (with `LC_ALL=C.UTF-8`), applies it to the whole diff including CLAUDE.md and .claude/, and spells out its result: 0 is clean (exit code 1 is normal for grep), anything else or exit code 2 is FAIL. reviewer diffs against origin/main instead of local main.
- Why: In this container's default locale, `grep -P` rejects the `\x{...}` range, so the scan silently never ran (first seen on PR #5). The 2026-11-27 trim had also limited the scan to files outside .claude/, but hidden characters there matter most. Local main was stale on PR #5, which made the diff show unrelated files.
- Source: Owner's request in chat, 2026-11-28.

## 2026-11-28: Phase 3 split: regional charts and validation wait for the levels formula
- Decision: At the owner's choice, this part of Phase 3 builds the 30-day slider, the monthly backfill, the History view and the almanac grid. The regional sparklines, series.csv and the validation gate wait until USF's AFAI-to-coverage formula is confirmed. A stand-in index ("AFAI above 0") was offered and declined.
- Why: Any regional number made now would be our own invention, and the validation gate would only test that invention.
- Source: Owner's answer in chat, 2026-11-28. The owner will upload USF's June, October and November 2025 bulletins for the validation later.

## 2026-11-28: Monthly maps: the mean of four 7-day frames, at stride 6
- Decision: Each month's map (public/data/monthly/YYYY-MM.png) is the pixel-by-pixel mean of that month's 7-day frames nearest days 7, 14, 21 and 28, at stride 6 (about 10 km), resampled to Mercator rows and encoded like the daily frames. A pixel with no data in all four frames stays no data. monthly.json lists each month's source frames and data fraction. Months with no frames at all (the data's 2016 gap) are skipped and, once more than two months old, remembered in `empty_months` so they aren't asked about again.
- Why: The mean of weekly composites is a simple, threshold-free picture of the month. It's a display choice, not a measurement; the regional index will be defined with the levels method. Which seven days each 7-day frame covers is still UNVERIFIED, so a month's map covers roughly days 1 to 28.
- Measured: June 2025 took 17 s (four downloads, 3 s pause before each) and made an 88,053-byte PNG (667 × 458). The full backfill: 125 months, June 2016 to October 2026, 10,446,211 bytes in all (about 84 KB a month, so about 1 MB a year from now on), in about 33 minutes on 2026-11-28, with one connection reset that a retry handled. Seven months (August 2016 to February 2017) have fewer than four frames because of the data's gap. June 2016 was first skipped: ERDDAP answers "no data" when a time range starts before the dataset's first frame (2016-06-18), so that month's request now starts there (DATA_START).
- Source: pipeline/src/sargasso_pipeline/monthly.py and pipeline/tests/test_monthly.py.

## 2026-11-28: New months arrive through the daily job, without blocking it
- Decision: After the daily update, the pipeline adds last month's map if it's missing (four extra downloads, once a month). If that fails, the daily map is still committed and the run shows a GitHub Actions warning ("Monthly map not updated"); the next run tries again.
- Why: A monthly hiccup shouldn't stop the daily map. The workflow commits only when the pipeline succeeds, so the monthly step reports a warning instead of failing. Making it a separate workflow step would need a .github edit, which this change avoids.
- Source: pipeline/src/sargasso_pipeline/__init__.py (update_monthly).

## 2026-11-28: Time views on the map page
- Decision: Three views: Now (latest frame), 30 days (slider and play over the daily frames on the site) and History (slider and play over the monthly maps, plus an almanac grid of years by months). Play waits until each frame is on screen before moving on. A tapped reading stays and follows the frame through time. The almanac grid only shows which months have a map and which one is chosen; it carries no index until the levels method exists.
- Why: Keeps one map and one legend for every view, and needs no number we can't yet justify.
- Almanac cells are 44 × 44 px at every width. On narrow screens the grid scrolls sideways inside its own box (the page never does), the year column stays pinned, and the chosen month is kept in view, also while playing (ui-reviewer, first run FAIL at about 25 px wide).
- Focus rings stay brass, as docs/PLAN.md's Design section specifies ("Focus ring: 1 px brass outline, 4 px offset"). ui-reviewer's "brass only in the scale" check flags this each time; PLAN.md decides it, and changing it is a design-direction question for the owner.
- Monthly maps look dimmer than daily ones: averaging four weeks softens short-lived patches. November 2017, for example, has data in 44% of the frame, but only 0.6% of those pixels are above AFAI 0.
- Source: app/now-view.tsx, app/sargassum-map.tsx.

## 2026-11-28: USF's 2025 bulletins (June, October, November), for the validation gate
- Decision: Use the owner's uploaded copies only for comparison; don't commit them or copy their images (docs/PLAN.md). Their regions, as drawn on the maps: 1 Gulf of Mexico, 2 Western Caribbean, 3 Eastern Caribbean, 4 West Atlantic, 5 East Atlantic.
- Totals (wet biomass, metric tons) — Jun 2025: Gulf 1.1M, W Caribbean 2.4M, E Caribbean 8.3M, W Atlantic 22M, E Atlantic 3.4M, all 33.5M. Oct 2025: <0.02M, 0.13M, 0.7M, 0.36M, 2.9M, all 4.3M. Nov 2025: <0.01M, 0.01M, 0.18M, 0.67M, 0.82M, all 1.71M.
- For the gate: region 5 extends east of our data's edge (38°W), so "all" includes ocean we don't cover. Regions 1–4 alone also fall from October to November (about 1.2M to 0.9M), but region 4 alone rises (0.36M to 0.67M), so compare totals, as PLAN.md says. The bulletins say their top color means about 0.4% of the ocean surface is covered; they give no AFAI-to-coverage formula, so the levels method stays open.
- Source: USF Optical Oceanography Lab, "Outlook of 2025 Sargassum blooms", issued July 1, October 31 and December 1, 2025 (files uploaded by the owner, 2026-11-28). Injection check: none found.

## 2026-11-28: Validation gate, June half: our June 2025 map matches USF's (qualitative)
- Decision: Mark the June half of the Phase 3 validation gate as passed, by eye, with the caveats below. The October-to-November half still waits for the levels formula.
- Why: Our June 2025 monthly map (docs/validation/june-2025-ours.png) is brightest in the same places as the "Sargassum distribution, June 2025" map in USF's bulletin: a band across the central and eastern Caribbean south of Hispaniola and Puerto Rico, the Lesser Antilles near 60°W, and the tropical Atlantic about 5–12°N east of 50°W. The box northeast of the Bahamas and the northern Gulf are quiet in both. As a rough check (for validation only, never shown on the site): of our brightest 2% of pixels, 44% lie east of 60°W, 28% in the eastern Caribbean (75–60°W), 26% in the western Caribbean (88–75°W) and 12% in the Gulf (98–81°W). That is the same order as USF's June totals (W Atlantic 22M, E Caribbean 8.3M, W Caribbean 2.4M, Gulf 1.1M metric tons).
- Caveats: some of our bright pixels hug coastlines (Cuba, Florida, Hispaniola), where USF masks; they likely pad our Gulf and western Caribbean shares. Our map is much less vivid than USF's: their top color is about 0.4% of the surface covered, a small AFAI signal, so on our continuous scale the belt reads as scattered bright specks. The longitude bands are rough stand-ins for USF's boxes.
- Source: USF June 2025 bulletin (owner's upload); our 2025-06 monthly map.
