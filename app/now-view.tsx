"use client";

// The "Now" view below the header: the map, the legend and the tap readout.
// MapLibre is large, so the map code loads after the page has appeared.

import dynamic from "next/dynamic";
import { useState } from "react";

import { decode, legendGradient, scalePosition, type Latest } from "@/lib/frame";
import type { MapStatus, Reading } from "./sargassum-map";

const SargassumMap = dynamic(() => import("./sargassum-map"), { ssr: false });

export default function NowView({ latest }: { latest: Latest }) {
  const [reading, setReading] = useState<Reading | null>(null);
  const [status, setStatus] = useState<MapStatus>("loading");

  return (
    <>
      <div className="map-wrap" role="region" aria-label="Map of sargassum levels">
        <SargassumMap latest={latest} onReading={setReading} onStatus={setStatus} />
        {status !== "ready" && (
          <p className="map-status" role="status">
            {status === "loading" ? "Loading the latest map…" : "The map couldn’t load. Please try again later."}
          </p>
        )}
      </div>

      <section className="panel" aria-label="Legend and reading">
        <div className="legend">
          <p className="cap label">Sargassum level (relative)</p>
          <div className="legend-bar" style={{ background: legendGradient() }} />
          <div className="legend-ends">
            <span>Lower</span>
            <span>Higher</span>
          </div>
          <p className="legend-nodata">
            <span className="swatch-hatch" aria-hidden="true" />
            No data: cloud, or outside the satellite product’s coverage
          </p>
        </div>

        <div className="readout" aria-live="polite" aria-atomic="true">
          <p className="cap label">Reading</p>
          <ReadingText reading={reading} latest={latest} />
        </div>

        <div className="notes">
          <p>
            A continuous, relative scale. Named levels (low, moderate, high) will follow once USF’s
            published method for them is confirmed.
          </p>
          <p>
            Bright pixels near coastlines may be shallow seafloor, sediment or mixed land–water
            pixels rather than sargassum; this map can’t yet tell them apart.
          </p>
          <p>
            {Math.round(latest.data_fraction * 100)}% of the frame has data in this composite; the
            rest is cloud, land or outside coverage.
          </p>
        </div>
      </section>
    </>
  );
}

function ReadingText({ reading, latest }: { reading: Reading | null; latest: Latest }) {
  if (!reading) {
    return (
      <p className="readout-hint">
        Tap the map for a reading. With a keyboard, focus the map and press Enter or Space to read
        its centre.
      </p>
    );
  }

  const place = <p className="coords">{formatLatLng(reading.lat, reading.lng)}</p>;
  if (reading.kind === "land") {
    return <>{place}<p>Land: no reading.</p></>;
  }
  if (reading.kind === "nodata") {
    return <>{place}<p>No data here in this composite (cloud, or outside the product’s coverage).</p></>;
  }

  // No number on a 0–100 scale: it would read like percent cover, and the
  // bottom of the scale isn't "no sargassum". The marker shows where the
  // reading sits on the legend, and the AFAI value is given as is.
  const enc = latest.encoding;
  const position = scalePosition(reading.code, enc) ?? 0;
  const afai = decode(reading.code, enc) ?? 0;
  let where = "marked on the scale above";
  if (reading.code === enc.last_code) where = "at the top of the scale";
  if (reading.code === enc.first_code) where = "at the bottom of the scale";

  return (
    <>
      {place}
      <div className="meter" style={{ background: legendGradient() }} aria-hidden="true">
        <span style={{ left: `${position * 100}%` }} />
      </div>
      <p>Relative level: {where}</p>
      <p className="afai">
        AFAI index {afai.toFixed(4)}
        {reading.code === enc.last_code ? " or more" : ""}
        {reading.code === enc.first_code ? " or less" : ""}. A relative index: not tons, percent
        cover or a forecast.
      </p>
    </>
  );
}

function formatLatLng(lat: number, lng: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lng >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}° ${ns} · ${Math.abs(lng).toFixed(2)}° ${ew}`;
}
