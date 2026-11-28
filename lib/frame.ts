// Helpers for reading the daily "data PNG" in the browser.
// Pure functions with no browser APIs, so `npm test` can check them with Node.
// The pipeline that writes the PNG is pipeline/src/sargasso_pipeline/.

/** The shape of public/data/latest.json (written by pipeline/output.py). */
export type Latest = {
  data_date: string; // YYYY-MM-DD
  time: string;
  composite: string;
  dataset_id: string;
  server: string;
  variable: string;
  index: string;
  image: string; // e.g. "daily/2026-11-26.png", relative to /data/
  width: number;
  height: number;
  data_fraction: number;
  bounds: { west: number; south: number; east: number; north: number };
  rows: string;
  encoding: Encoding;
  levels: {
    names: string[];
    breaks_afai: number[] | null;
    breaks_code: number[] | null;
    status: string;
  };
  daily_frames: string[];
};

/** The shape of public/data/monthly.json (written by pipeline/monthly.py). */
export type Monthly = {
  composite: string;
  stride: number;
  width: number;
  height: number;
  bounds: { west: number; south: number; east: number; north: number };
  encoding: Encoding;
  months: { month: string; frames: string[]; data_fraction: number }[];
};

/** Everything the map needs to draw one frame and read its pixels. */
export type FrameSpec = {
  key: string; // "2026-11-27" for a daily frame, "2025-06" for a month
  kind: "daily" | "monthly";
  image: string; // relative to /data/
  width: number;
  height: number;
  bounds: { west: number; south: number; east: number; north: number };
  encoding: Encoding;
  dataFraction: number | null; // share of pixels with data, when known
};

/** The image grid: what pixelAt needs. */
type Grid = Pick<FrameSpec, "bounds" | "width" | "height">;

/** The latest daily frame, and every daily frame still on the site (oldest first). */
export function dailySpecs(latest: Latest): FrameSpec[] {
  return [...latest.daily_frames].sort().map((date) => ({
    key: date,
    kind: "daily",
    image: `daily/${date}.png`,
    width: latest.width,
    height: latest.height,
    bounds: latest.bounds,
    encoding: latest.encoding,
    dataFraction: date === latest.data_date ? latest.data_fraction : null,
  }));
}

/** One frame per month in monthly.json, oldest first. */
export function monthlySpecs(monthly: Monthly | null): FrameSpec[] {
  if (!monthly) return [];
  return [...monthly.months]
    .sort((a, b) => a.month.localeCompare(b.month))
    .map((m) => ({
      key: m.month,
      kind: "monthly",
      image: `monthly/${m.month}.png`,
      width: monthly.width,
      height: monthly.height,
      bounds: monthly.bounds,
      encoding: monthly.encoding,
      dataFraction: m.data_fraction,
    }));
}

export type Encoding = {
  nodata: number;
  first_code: number;
  last_code: number;
  afai_min: number;
  afai_max: number;
};

type RGB = [number, number, number];

/** Web Mercator y (in radians) for a latitude in degrees. Same formula as grid.py. */
export function mercatorY(latDeg: number): number {
  const lat = (latDeg * Math.PI) / 180;
  return Math.log(Math.tan(Math.PI / 4 + lat / 2));
}

/**
 * Which PNG pixel covers a point, or null if the point is outside the image.
 * Columns are evenly spaced in longitude; rows are evenly spaced in Web
 * Mercator, with north at the top (see grid.py's to_mercator_rows).
 */
export function pixelAt(latest: Grid, lng: number, lat: number): { x: number; y: number } | null {
  const { west, east, south, north } = latest.bounds;
  if (lng < west || lng >= east || lat <= south || lat > north) return null;
  const x = Math.floor(((lng - west) / (east - west)) * latest.width);
  const top = mercatorY(north);
  const bottom = mercatorY(south);
  const y = Math.floor(((top - mercatorY(lat)) / (top - bottom)) * latest.height);
  return { x: Math.min(x, latest.width - 1), y: Math.min(y, latest.height - 1) };
}

/** A PNG code back to the AFAI value, or null for "no data". Same as encode.py's decode. */
export function decode(code: number, enc: Encoding): number | null {
  if (code === enc.nodata) return null;
  const step = (enc.afai_max - enc.afai_min) / (enc.last_code - enc.first_code);
  return enc.afai_min + (code - enc.first_code) * step;
}

/** Where a code sits on the legend: 0 at the bottom of the scale, 1 at the top. */
export function scalePosition(code: number, enc: Encoding): number | null {
  if (code === enc.nodata) return null;
  return (code - enc.first_code) / (enc.last_code - enc.first_code);
}

// The level scale (docs/PLAN.md, Design): from the ink ground, through dim
// stone and brass, to a bright gold. Each stop is lighter than the one before,
// so the scale reads in grayscale and for color-blind viewers. The lowest
// third stays close to ink, so calm ocean looks like the ocean ground and only
// higher values stand out. It's a continuous display stretch over the data's
// own range (AFAI -0.002 to 0.004), not level classes.
export const SCALE_STOPS: [number, RGB][] = [
  [0, [0x1b, 0x1c, 0x1a]], // a hair above the ink ground (#191a18)
  [0.3, [0x2a, 0x29, 0x25]], // still close to ink
  [0.55, [0x6b, 0x64, 0x58]], // dim stone
  [0.8, [0xa8, 0x84, 0x5a]], // brass
  [1, [0xf2, 0xd0, 0x80]], // bright gold
];

/** The scale's color at position t (0 to 1), blending between stops. */
export function colorAt(t: number): RGB {
  const clamped = Math.min(1, Math.max(0, t));
  for (let i = 1; i < SCALE_STOPS.length; i++) {
    const [t1, c1] = SCALE_STOPS[i];
    if (clamped <= t1) {
      const [t0, c0] = SCALE_STOPS[i - 1];
      const f = (clamped - t0) / (t1 - t0);
      return [0, 1, 2].map((k) => Math.round(c0[k] + (c1[k] - c0[k]) * f)) as RGB;
    }
  }
  return SCALE_STOPS[SCALE_STOPS.length - 1][1];
}

/** CSS gradient for the legend bar, built from the same stops as the map. */
export function legendGradient(): string {
  const parts = SCALE_STOPS.map(([t, c]) => `rgb(${c.join(" ")}) ${Math.round(t * 100)}%`);
  return `linear-gradient(to right, ${parts.join(", ")})`;
}

/** Lookup table: 256 RGBA entries, one per PNG code. Code 0 (no data) is transparent. */
export function buildLut(enc: Encoding): Uint8ClampedArray {
  const lut = new Uint8ClampedArray(256 * 4);
  for (let code = 0; code < 256; code++) {
    const t = scalePosition(code, enc);
    if (t === null || code < enc.first_code || code > enc.last_code) continue; // stays transparent
    const [r, g, b] = colorAt(t);
    lut.set([r, g, b, 255], code * 4);
  }
  return lut;
}

/** Color an image's codes with the lookup table. `codes` has one byte per pixel. */
export function colorize(codes: Uint8Array, lut: Uint8ClampedArray): Uint8ClampedArray {
  const rgba = new Uint8ClampedArray(codes.length * 4);
  for (let i = 0; i < codes.length; i++) {
    const at = codes[i] * 4;
    rgba[i * 4] = lut[at];
    rgba[i * 4 + 1] = lut[at + 1];
    rgba[i * 4 + 2] = lut[at + 2];
    rgba[i * 4 + 3] = lut[at + 3];
  }
  return rgba;
}

/** Relative luminance (WCAG) of an sRGB color, 0 (black) to 1 (white). */
export function luminance([r, g, b]: RGB): number {
  const lin = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

export const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];

/** "2026-11-26" → "26 November 2026" (read as a calendar date, not a local time). */
export function formatDataDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return `${d} ${MONTH_NAMES[m - 1]} ${y}`;
}

/** "2025-06" → "June 2025". */
export function formatMonth(isoMonth: string): string {
  const [y, m] = isoMonth.split("-").map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

/** A frame's date as shown on screen. */
export function formatFrame(spec: Pick<FrameSpec, "key" | "kind">): string {
  return spec.kind === "monthly" ? formatMonth(spec.key) : formatDataDate(spec.key);
}
