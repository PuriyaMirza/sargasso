"use client";

// Everything below the title: which frame to show (Now, the last 30 days, or
// History), the map, the legend and the tap readout.
// MapLibre is large, so the map code loads after the page has appeared.

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import {
  dailySpecs,
  decode,
  formatFrame,
  legendGradient,
  monthlySpecs,
  MONTH_NAMES,
  scalePosition,
  type FrameSpec,
  type Latest,
  type Monthly,
} from "@/lib/frame";
import type { MapStatus, Reading } from "./sargassum-map";

const SargassumMap = dynamic(() => import("./sargassum-map"), { ssr: false });

type View = "now" | "days" | "history";
const PLAY_STEP_MS = 700; // how long each frame stays up while playing

export default function NowView({ latest, monthly }: { latest: Latest; monthly: Monthly | null }) {
  const days = useMemo(() => dailySpecs(latest), [latest]);
  const months = useMemo(() => monthlySpecs(monthly), [monthly]);
  const latestIndex = Math.max(0, days.findIndex((d) => d.key === latest.data_date));

  const [view, setView] = useState<View>("now");
  const [dayIndex, setDayIndex] = useState(days.length - 1);
  const [monthIndex, setMonthIndex] = useState(months.length - 1);
  const [playing, setPlaying] = useState(false);
  const [shownKey, setShownKey] = useState<string | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [status, setStatus] = useState<MapStatus>("loading");

  const frames = view === "history" ? months : days;
  const index = view === "history" ? monthIndex : view === "days" ? dayIndex : latestIndex;
  const setIndex = view === "history" ? setMonthIndex : setDayIndex;
  const frame: FrameSpec = frames[index] ?? days[latestIndex];

  // Playing: once the current frame is on screen, wait a moment, then step on.
  // Stops at the last frame.
  useEffect(() => {
    if (!playing || shownKey !== frame.key) return;
    const atEnd = index >= frames.length - 1;
    const timer = setTimeout(() => (atEnd ? setPlaying(false) : setIndex(index + 1)), PLAY_STEP_MS);
    return () => clearTimeout(timer);
  }, [playing, shownKey, frame.key, index, frames.length, setIndex]);

  function choose(next: View) {
    setPlaying(false);
    setView(next);
  }

  function togglePlay() {
    if (!playing && index >= frames.length - 1) setIndex(0); // start again from the beginning
    setPlaying(!playing);
  }

  const isMonth = frame.kind === "monthly";

  return (
    <>
      <div className="when">
        <p className="cap label">{isMonth ? "Month" : "Data date"}</p>
        <p className="date">
          <time dateTime={frame.key}>{formatFrame(frame)}</time>
        </p>
        <p className="sub">
          {isMonth
            ? "Average of the month’s 7-day composites"
            : view === "days"
              ? `7-day composite · ${index + 1} of ${frames.length} on the site`
              : "7-day composite"}
        </p>
      </div>

      <div className="map-wrap" role="region" aria-label="Map of sargassum levels">
        <SargassumMap frame={frame} onReading={setReading} onStatus={setStatus} onFrameShown={setShownKey} />
        {status !== "ready" && (
          <p className="map-status" role="status">
            {status === "loading" ? "Loading the map…" : "The map couldn’t load. Please try again later."}
          </p>
        )}
      </div>

      <section className="controls" aria-label="Time">
        <div className="views" role="group" aria-label="Show">
          <ViewButton current={view} value="now" onChoose={choose}>Now</ViewButton>
          <ViewButton current={view} value="days" onChoose={choose} disabled={days.length < 2}>30 days</ViewButton>
          <ViewButton current={view} value="history" onChoose={choose} disabled={months.length === 0}>History</ViewButton>
        </div>

        {view !== "now" && (
          <div className="scrub">
            <button type="button" className="play" onClick={togglePlay} aria-pressed={playing}>
              {playing ? "Pause" : "Play"}
            </button>
            <input
              type="range"
              min={0}
              max={frames.length - 1}
              step={1}
              value={index}
              onChange={(e) => {
                setPlaying(false);
                setIndex(Number(e.target.value));
              }}
              aria-label={view === "history" ? "Month" : "Day"}
              aria-valuetext={formatFrame(frame)}
            />
          </div>
        )}
        {view === "days" && (
          <p className="hint">
            The site keeps the last 30 daily frames; this slider grows as new ones arrive.
          </p>
        )}

        {view === "history" && (
          <Almanac
            months={months}
            selected={frame.key}
            onPick={(i) => {
              setPlaying(false);
              setMonthIndex(i);
            }}
          />
        )}
      </section>

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
          <ReadingText reading={reading} frame={frame} />
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
          {frame.dataFraction !== null && (
            <p>
              {Math.round(frame.dataFraction * 100)}% of the frame has data
              {isMonth ? " this month" : " in this composite"}; the rest is cloud, land or outside
              coverage.
            </p>
          )}
          {isMonth && (
            <p>
              Monthly maps are coarser (about 10 km per pixel) than the daily ones (about 7 km).
            </p>
          )}
        </div>
      </section>
    </>
  );
}

function ViewButton({
  current,
  value,
  onChoose,
  disabled,
  children,
}: {
  current: View;
  value: View;
  onChoose: (v: View) => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button type="button" aria-pressed={current === value} disabled={disabled} onClick={() => onChoose(value)}>
      {children}
    </button>
  );
}

// The almanac grid: one row per year, one column per month. Months with a
// map are buttons; the chosen month is filled. Echoes the page's column lines.
function Almanac({
  months,
  selected,
  onPick,
}: {
  months: FrameSpec[];
  selected: string;
  onPick: (index: number) => void;
}) {
  const byKey = new Map(months.map((m, i) => [m.key, i]));
  const years = [...new Set(months.map((m) => m.key.slice(0, 4)))];
  return (
    <div className="almanac" role="group" aria-label="Pick a month">
      <div className="almanac-row almanac-head" aria-hidden="true">
        <span />
        {MONTH_NAMES.map((name) => (
          <span key={name}>{name[0]}</span>
        ))}
      </div>
      {years.map((year) => (
        <div className="almanac-row" key={year}>
          <span className="almanac-year">{year}</span>
          {MONTH_NAMES.map((name, m) => {
            const key = `${year}-${String(m + 1).padStart(2, "0")}`;
            const i = byKey.get(key);
            if (i === undefined) return <span key={key} className="almanac-empty" aria-hidden="true" />;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={key === selected}
                aria-label={`${name} ${year}`}
                onClick={() => onPick(i)}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}

function ReadingText({ reading, frame }: { reading: Reading | null; frame: FrameSpec }) {
  if (!reading) {
    return (
      <p className="readout-hint">
        Tap the map for a reading. With a keyboard, focus the map and press Enter or Space to read
        its centre. The reading follows the frame as you move through time.
      </p>
    );
  }

  const place = <p className="coords">{formatLatLng(reading.lat, reading.lng)}</p>;
  if (reading.kind === "land") {
    return <>{place}<p>Land: no reading.</p></>;
  }
  if (reading.kind === "nodata") {
    return <>{place}<p>No valid reading here in this {frame.kind === "monthly" ? "month" : "composite"} (for example cloud, or outside the product’s coverage).</p></>;
  }

  // No number on a 0–100 scale: it would read like percent cover, and the
  // bottom of the scale isn't "no sargassum". The marker shows where the
  // reading sits on the legend, and the AFAI value is given as is.
  const enc = frame.encoding;
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
