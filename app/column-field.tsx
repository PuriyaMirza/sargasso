"use client";

// The Almanac background: faint vertical lines across the page, with one line
// at a time glowing softly. Ported from the owner's portfolio script.
// The lines sit behind the content and ignore taps (see .lines in globals.css).

import { useEffect, useRef } from "react";

const PULSE_MS = 1400; // how long one glow lasts
const RISE = 0.38; // share of the glow spent fading in
const BEAT_MS = 1000; // a new line starts glowing every second

type Line = { glow: HTMLElement; start: number; y: number };

// S-shaped easing: starts and ends gently.
const smooth = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

export default function ColumnField() {
  const layerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const layer = layerRef.current;
    const frame = document.querySelector<HTMLElement>(".frame");
    if (!layer || !frame) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let lines: Line[] = [];
    let bag: number[] = [];
    let last = -1;
    let raf = 0;
    let stopped = false;

    // Draw one line per column edge, spread across the content column.
    function build() {
      if (stopped || !layer || !frame) return;
      const root = document.documentElement;
      const count = parseInt(getComputedStyle(root).getPropertyValue("--lines"), 10) || 18;
      const box = frame.getBoundingClientRect();
      layer.replaceChildren();
      lines = [];
      bag = [];
      for (let c = 0; c <= count; c++) {
        const line = document.createElement("div");
        line.className = "line";
        line.style.left = `${Math.round(box.left + (box.width / count) * c)}px`;
        const glow = document.createElement("i");
        line.appendChild(glow);
        layer.appendChild(line);
        lines.push({ glow, start: -1e9, y: 0 });
      }
    }

    // Animate every glowing line for one frame; keep going while any is lit.
    function tick(now: number) {
      let anyLit = false;
      const height = lines.length ? lines[0].glow.offsetHeight : 0;
      for (const line of lines) {
        const t = (now - line.start) / PULSE_MS;
        let opacity = 0;
        if (t >= 0 && t < 1) {
          opacity = t < RISE ? smooth(t / RISE) : 1 - smooth((t - RISE) / (1 - RISE));
          anyLit = true;
        }
        line.glow.style.opacity = opacity.toFixed(3);
        if (opacity > 0) line.glow.style.transform = `translateY(${Math.round(line.y - height / 2)}px)`;
      }
      raf = anyLit ? requestAnimationFrame(tick) : 0;
    }

    // Shuffle the lines so each one glows once before any repeats.
    function nextIndex() {
      if (!bag.length) {
        bag = lines.map((_, i) => i);
        for (let i = bag.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [bag[i], bag[j]] = [bag[j], bag[i]];
        }
        if (bag.length > 1 && bag[bag.length - 1] === last) {
          [bag[0], bag[bag.length - 1]] = [bag[bag.length - 1], bag[0]];
        }
      }
      return bag.pop();
    }

    function beat() {
      if (reduceMotion.matches || document.hidden || !lines.length) return;
      const i = nextIndex();
      if (i === undefined || !lines[i]) return;
      last = i;
      lines[i].start = performance.now();
      lines[i].y = window.innerHeight * (0.15 + Math.random() * 0.7);
      if (!raf) raf = requestAnimationFrame(tick);
    }

    build();
    window.addEventListener("resize", build);
    document.fonts?.ready.then(build); // fonts can shift the layout, so rebuild once they load
    const timer = window.setInterval(beat, BEAT_MS);

    return () => {
      stopped = true;
      window.clearInterval(timer);
      window.removeEventListener("resize", build);
      cancelAnimationFrame(raf);
    };
  }, []);

  return <div className="lines" ref={layerRef} aria-hidden="true" />;
}
