// Run with `npm test`. Node runs TypeScript directly; no extra tools needed.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  buildLut,
  colorAt,
  colorize,
  decode,
  formatDataDate,
  luminance,
  pixelAt,
  scalePosition,
  type Latest,
} from "./frame.ts";

const latest: Latest = JSON.parse(readFileSync("public/data/latest.json", "utf8"));

test("points land on the same PNG pixels the Python pipeline computes", () => {
  // Expected values computed in Python from latest.json with the formulas in
  // grid.py (see docs/DECISIONS.md, Phase 2), not with this file's code.
  const expected: [string, number, number, number, number][] = [
    ["Barbados", -59.55, 13.17, 641, 464],
    ["Puerto Rico", -66.5, 18.2, 525, 377],
    ["Mérida", -89.6, 20.97, 140, 328],
    ["south-west corner", -98.0, 0.0, 0, 686],
    ["north-east corner", -38.0, 38.0, 1000, 0],
  ];
  for (const [name, lng, lat, x, y] of expected) {
    assert.deepEqual(pixelAt(latest, lng, lat), { x, y }, name);
  }
});

test("points outside the image have no pixel", () => {
  assert.equal(pixelAt(latest, -100, 20), null);
  assert.equal(pixelAt(latest, -60, 40), null);
  assert.equal(pixelAt(latest, -60, -1), null);
});

test("decode matches the encoding in latest.json", () => {
  const enc = latest.encoding;
  assert.equal(decode(0, enc), null);
  assert.equal(decode(1, enc), enc.afai_min);
  assert.ok(Math.abs((decode(255, enc) as number) - enc.afai_max) < 1e-12);
  assert.equal(scalePosition(0, enc), null);
  assert.equal(scalePosition(1, enc), 0);
  assert.equal(scalePosition(255, enc), 1);
});

test("the color scale gets lighter all the way up", () => {
  let previous = -1;
  for (let i = 0; i <= 254; i++) {
    const l = luminance(colorAt(i / 254));
    assert.ok(l >= previous, `step ${i} is darker than step ${i - 1}`);
    previous = l;
  }
  // The top of the scale is clearly visible on the ink ground (WCAG 3:1 for graphics).
  const ink = luminance([0x19, 0x1a, 0x18]);
  const top = luminance(colorAt(1));
  assert.ok((top + 0.05) / (ink + 0.05) >= 3);
});

test("no data stays transparent and data is opaque", () => {
  const lut = buildLut(latest.encoding);
  const rgba = colorize(new Uint8Array([0, 1, 128, 255]), lut);
  assert.equal(rgba[3], 0); // code 0: transparent
  assert.equal(rgba[7], 255);
  assert.equal(rgba[11], 255);
  assert.equal(rgba[15], 255);
  assert.deepEqual([...rgba.slice(12, 15)], colorAt(1));
});

test("data dates read as calendar dates", () => {
  assert.equal(formatDataDate("2026-11-26"), "26 November 2026");
  assert.equal(formatDataDate("2027-01-03"), "3 January 2027");
});
