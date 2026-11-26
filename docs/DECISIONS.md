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
  - Wang and Hu 2016, Remote Sensing of Environment 183:350–367, doi:10.1016/j.rse.2016.04.019 (UNVERIFIED, search snippets only): detection threshold 1.79e-4 (AFAI above background); AFAI -8.77e-4 = 0% coverage and 4.41e-2 = 100% coverage, with a linear mapping between them. These numbers are for MODIS. Note that ERDDAP's `actual_range` tops out at 0.004, far below the 100% value, so the ERDDAP values may be clipped. Check this in Phase 1.
  - USF SaWS: describes a density product with a color scale of 0.00–0.10 ‰ (per mille), but gives no conversion steps. https://optics.marine.usf.edu/projects/saws.html
  - NOAA SIR: risk classes low, warning, medium and high against a multi-day baseline. The 0.001 and 0.003 thresholds in docs/PLAN.md were not found on the page. https://cwcgom.aoml.noaa.gov/SIR/
  - Blocked: doi.org, www.sciencedirect.com and repository.library.noaa.gov (DNS failure); sargcoop.org and digitalcommons.usf.edu (network proxy 403).
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
