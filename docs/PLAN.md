# Sargassum Map: plan

## Goal
Show where sargassum is this week across the Caribbean, Gulf of Mexico and western Atlantic, and how this season compares with every season since 2016. This is monitoring, not forecasting: for Puerto Rico, link to the CARICOOS 7-day forecast at https://www.caricoos.org/sargassum. Target: v1 live by Jan 18, 2027.

## Data
- Main: USF AFAI on NOAA ERDDAP, https://cwcgom.aoml.noaa.gov/erddap/griddap/noaa_aoml_atlantic_oceanwatch_AFAI_7D.html (also _1D and _3D). Grid 0.015 degrees (2534 latitudes x 4001 longitudes), 0 to 38N, 98W to 38W, daily since 2016-06-18, timestamps at 12:00Z. License: free to use and redistribute, not for legal use.
- Mirror, fallback only: upwell.pfeg.noaa.gov (7-day USF AFAI).
- Validation only: USF monthly outlook bulletins, https://optics.marine.usf.edu/projects/saws.html (regional totals in metric tons). Don't copy their images.
- Coastal method model: NOAA Sargassum Inundation Risk, https://cwcgom.aoml.noaa.gov/SIR/ (AFAI within 50 km of each coastal pixel compared with a multi-day baseline; thresholds 0.001 and 0.003; experimental).
- Phase 4 stretch: CARICOOS biomass stations, https://dm3.caricoos.org/erddap/tabledap/Sargassum_Biomass_SC.html
- Basemap: Natural Earth 1:10m land (public domain), from the world-atlas npm package or the nvkelso/natural-earth-vector GitHub repo, clipped to the region once.

## Architecture
A daily GitHub Actions job (Python) fetches the newest 7-day AFAI frame, classifies it into levels, resamples rows to Web Mercator, encodes an 8-bit grayscale "data PNG" and commits it to public/data. Vercel rebuilds the Next.js site. MapLibre GL JS shows the frame, and the browser colors the data PNG with a lookup table. No database, no API keys, no server code.

Files under public/data/:
- latest.json: data date, dataset ID, bounds, class breaks, encoding scale, per-region stats
- daily/YYYY-MM-DD.png: 7-day composite at stride 3 (about 5 km), rolling 30 days
- monthly/YYYY-MM.png: monthly composite at stride 6 (about 10 km), Jun 2016 to now
- series.csv: date, region, index
- land.geojson: Natural Earth land clipped to the region

Encoding: 0 = no data (cloud, land, missing); 1 to 255 = scaled index. MapLibre draws an image as a straight quad between its corners in Web Mercator, so latitude rows must be resampled to Mercator spacing before encoding. Test it.

## Levels
- Classes: none, low, moderate, high, plus no data. Breaks come from USF's published method for turning AFAI into sargassum coverage (data-scout finds it; science-reviewer checks it). No guessed thresholds.
- On-screen label: "Sargassum level (relative)". Never tons, never "forecast".
- Validation gate (Phase 3): our June 2025 monthly map shows high levels in the same areas as the USF June 2025 bulletin map, and our regional index falls from October to November 2025 as the bulletin totals did (4.3M to 1.7M metric tons).

## Design
- Style: the owner's portfolio "Almanac" look. Reference implementation (CSS and the column-line pulse script): https://raw.githubusercontent.com/PuriyaMirza/personal-website/main/projects/index.html. Reuse its approach; it's the owner's own code. Dark only (color-scheme: dark).
- Tokens as CSS variables: --ink #191a18 (ground), --paper #f6f3ee (text), --stone #a39b8c (secondary text, control borders), --brass #a8845a, --frame-line #5b5d58 (hairlines only: 2.6:1 on ink, never text).
- Type (Google Fonts): Cormorant 300 and 300 italic for display (title, data date, big figures); Jost 300 and 400 for body at 16 px; labels 12 px, weight 400, uppercase, letter-spacing 0.14em. Focus ring: 1 px brass outline, 4 px offset.
- Background: the Almanac hairline column field: fixed vertical lines at 4% paper opacity (18 on desktop, 9 under 1000 px, 6 under 600 px), with the soft pulse from the reference (peak 28%, about 1.4 s). Lines sit behind content and never over the map's data. No pulse under prefers-reduced-motion.
- Color means data: brass is reserved for sargassum. The level scale runs from dim stone through brass to a bright gold, rising in lightness so it reads in grayscale and for color-blind viewers (check it with a simulator). Controls use paper and stone only.
- Map: ocean is the ink ground; land is one step lighter than ink with a frame-line coastline; no data is a faint paper hatch.
- Mobile first at 390 px: map on top, controls below. 44 px touch targets, WCAG AA contrast (on ink: paper 15.8:1, stone 6.3:1, brass 5.1:1).
- Views: Now (latest map, legend, data date, tap readout); Last 30 days (slider with play); History (monthly frames with play, plus an almanac grid of years by months that echoes the column rhythm); Regions (sparklines; regions approximate USF's and say so).
- Footer on every page: "Data: USF Optical Oceanography Lab, College of Marine Science, via NOAA AOML CoastWatch/OceanWatch ERDDAP. Experimental; may contain inaccuracies; not for navigation or legal use. Basemap: Made with Natural Earth."

## Phases (each ends with /phase-check and a PR)

### Phase 0: setup (target Nov 30)
Plan files, subagents, approval gate, Next.js and pipeline skeletons.
Phase 0 checks, run by data-scout as three parallel tasks:
1. ERDDAP: confirm the dataset IDs, axis order, latest timestamp, roughly what time each day a new date appears, and the size of one full-region 7-day frame as .nc at stride 3 and at stride 6.
2. Mirror: confirm upwell.pfeg.noaa.gov serves the same 7-day data, and note its dataset ID.
3. Method: find USF's published method for turning AFAI into sargassum coverage (for example Wang and Hu 2016, later USF papers, the SaWS pages). Return the steps and any thresholds with citations.
Done when: the Vercel preview deploys, pytest passes, the hook test passes, and the findings are in docs/DECISIONS.md.

### Phase 1: data pipeline (target Dec 7)
Fetch, classify, reproject, encode and write the files; a GitHub Action that runs daily and on manual trigger; mirror fallback; a loud failure when both servers fail, keeping the last good frame.
Done when: one real frame is committed; pytest covers axis order, Mercator resampling, the encoding round trip and the class breaks on synthetic data; geo-qa passes; measured file sizes are in DECISIONS.md.
Storage gate: if a daily frame is over 300 KB, or estimated repo growth is over 100 MB a year, stop and propose object storage.

### Phase 2: map MVP (target Dec 14)
MapLibre map with the land layer, latest frame, legend, data date, tap readout and footer, in the Almanac style.
Done when: the preview works on a phone at 390 px; the frame lines up with coastlines at Puerto Rico, Barbados and the Yucatan (geo-qa screenshot check); ui-reviewer passes; first load is under 1 MB excluding map frames.

### Phase 3: time and history (target Jan 4)
30-day slider with play; one-off monthly backfill from Jun 2016 to now with polite pacing; history view with play; almanac grid; regional sparklines.
Done when: the validation gate passes and is written up in DECISIONS.md with screenshots.

### Phase 4: coastal risk (target Jan 18, v1 live)
Coastal risk layer modeled on NOAA's method, labeled experimental; CARICOOS forecast link for Puerto Rico. Stretch, only if the owner agrees: CARICOOS station readings; an island lens showing which coasts face sargassum within 50 km.
Done when: science-reviewer passes and v1 is live on the production URL.

### Phase 5: polish and case study (after the trip)
Speed, empty and error states, a share link per date (#YYYY-MM-DD in the URL), and a case-study draft in docs/CASE_STUDY.md.
