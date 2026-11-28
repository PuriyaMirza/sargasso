"use client";

// The map: MapLibre with no outside tiles. Layers, bottom to top:
//   ocean (ink) → no-data hatch → the chosen frame → land → coastline.
// A frame is a grayscale "data PNG"; we color it here with the lookup table
// from lib/frame.ts and hand MapLibre the colored copy. The map is created
// once; changing the `frame` prop swaps the picture (for the 30-day slider
// and the History view). Frames already seen are kept, so play is smooth.

import "maplibre-gl/dist/maplibre-gl.css";

import type { ImageSource, Map as MapLibreMap, Marker } from "maplibre-gl";
import { useEffect, useRef } from "react";

import { buildLut, colorize, pixelAt, type FrameSpec } from "@/lib/frame";

export type Reading =
  | { kind: "land"; lng: number; lat: number }
  | { kind: "nodata"; lng: number; lat: number }
  | { kind: "value"; lng: number; lat: number; code: number };

export type MapStatus = "loading" | "ready" | "error";

const INK = "#191a18";
const LAND = "#2e2f2b"; // one step lighter than ink
const FRAME_LINE = "#5b5d58";
const HATCH_LINE = [0xf6, 0xf3, 0xee, 0.12] as const; // paper at 12%

type Props = {
  frame: FrameSpec;
  onReading: (reading: Reading) => void;
  onStatus: (status: MapStatus) => void;
  /** Called once the chosen frame is on screen, with its key. */
  onFrameShown?: (key: string) => void;
};

type Loaded = { codes: Uint8Array; url: string };

export default function SargassumMap({ frame, onReading, onStatus, onFrameShown }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Keep the newest callbacks and frame without re-creating the map when they change.
  const callbacks = useRef({ onReading, onStatus, onFrameShown });
  const frameRef = useRef(frame);
  useEffect(() => {
    callbacks.current = { onReading, onStatus, onFrameShown };
  });
  // Set by the map effect below: shows a frame, and is safe to call any time.
  const showRef = useRef<(spec: FrameSpec) => void>(() => {});
  useEffect(() => {
    frameRef.current = frame;
    showRef.current(frame);
  }, [frame]);

  useEffect(() => {
    let map: MapLibreMap | undefined;
    let marker: Marker | undefined;
    let shown: { spec: FrameSpec; codes: Uint8Array } | undefined; // the frame on screen
    let lastTap: { lng: number; lat: number } | undefined;
    let mapLoaded = false;
    let request = 0; // newest show() call; older loads are dropped when they finish
    let stopped = false; // set when the component unmounts
    const cache = new Map<string, Promise<Loaded>>(); // image path -> loaded frame, oldest use first
    const CACHE_LIMIT = 40; // frames kept in memory (each about 1 MB once decoded and colored)
    const { west, south, east, north } = frameRef.current.bounds; // first view

    async function start() {
      const maplibre = await import("maplibre-gl");
      if (stopped || !containerRef.current) return;
      // Where MapLibre finds its web worker: scripts/copy-maplibre-worker.mjs
      // puts it there before each build. This is a global setting, so setting
      // it again on a later mount is harmless.
      maplibre.setWorkerUrl(`/maplibre/maplibre-gl-worker.mjs?v=${maplibre.getVersion()}`);

      map = new maplibre.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {},
          layers: [{ id: "ocean", type: "background", paint: { "background-color": INK } }],
        },
        bounds: [[west, south], [east, north]],
        fitBoundsOptions: { padding: 8 },
        maxBounds: [[-115, -12], [-21, 50]],
        minZoom: 1,
        maxZoom: 9,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        fadeDuration: 0,
        hash: "map", // keeps the view in the address, e.g. #map=6/18.2/-66.4, so links can be shared
        attributionControl: {
          compact: true,
          customAttribution: "USF Optical Oceanography Lab · NOAA ERDDAP · Natural Earth",
        },
      });
      map.touchZoomRotate.disableRotation();
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");

      const ring = document.createElement("div");
      ring.className = "tap-marker";
      marker = new maplibre.Marker({ element: ring });

      map.on("load", async () => {
        if (!map) return;
        map.addImage("hatch", hatchPattern(), { pixelRatio: 2 });
        map.addLayer({ id: "nodata-hatch", type: "background", paint: { "background-pattern": "hatch" } });
        map.addSource("land", { type: "geojson", data: "/data/land.geojson" });
        map.addLayer({ id: "land", type: "fill", source: "land", paint: { "fill-color": LAND } });
        map.addLayer({
          id: "coast",
          type: "line",
          source: "land",
          paint: { "line-color": FRAME_LINE, "line-width": 0.75 },
        });

        mapLoaded = true;
        show(frameRef.current);
      });

      // Log every map error. Only show the "couldn't load" message if the
      // frame isn't up yet; a later hiccup shouldn't hide a working map.
      map.on("error", (event) => {
        console.error("Map error:", event.error ?? event);
        if (!stopped && !shown) callbacks.current.onStatus("error");
      });

      // A tap (or click) gives a reading for that spot.
      map.on("click", (event) => {
        read(event.lngLat.lng, event.lngLat.lat, event.point);
      });

      // Keyboard: Enter or Space reads the centre of the map.
      map.getCanvas().addEventListener("keydown", (event) => {
        if (!map || (event.key !== "Enter" && event.key !== " ")) return;
        event.preventDefault();
        const centre = map.getCenter();
        read(centre.lng, centre.lat, map.project(centre));
      });
    }

    function load(spec: FrameSpec): Promise<Loaded> {
      let loaded = cache.get(spec.image);
      if (loaded) {
        cache.delete(spec.image); // move to the newest end
        cache.set(spec.image, loaded);
      } else {
        loaded = loadCodes(`/data/${spec.image}`, spec.width, spec.height).then(async (codes) => ({
          codes,
          url: await coloredImageUrl(codes, spec),
        }));
        loaded.catch(() => cache.delete(spec.image)); // let a later attempt retry
        cache.set(spec.image, loaded);
        // Drop the least recently used frames, except the one on screen.
        for (const [image, old] of cache) {
          if (cache.size <= CACHE_LIMIT) break;
          if (image === shown?.spec.image || image === spec.image) continue;
          cache.delete(image);
          old.then((l) => URL.revokeObjectURL(l.url), () => {});
        }
      }
      return loaded;
    }

    // Put a frame on the map. Fast slider moves call this many times; only
    // the newest call's frame is drawn.
    async function show(spec: FrameSpec) {
      if (!map || !mapLoaded) return; // the load handler calls show() again
      const mine = ++request;
      let loaded: Loaded;
      try {
        loaded = await load(spec);
      } catch (err) {
        console.error(`Couldn't load the frame ${spec.key}:`, err);
        if (!stopped && mine === request) callbacks.current.onStatus("error");
        return;
      }
      if (stopped || !map || mine !== request) return;
      const b = spec.bounds;
      const coordinates: [[number, number], [number, number], [number, number], [number, number]] = [
        [b.west, b.north], [b.east, b.north], [b.east, b.south], [b.west, b.south],
      ];
      const source = map.getSource("frame") as ImageSource | undefined;
      if (source) {
        source.updateImage({ url: loaded.url, coordinates });
      } else {
        map.addSource("frame", { type: "image", url: loaded.url, coordinates });
        // Insert the frame under the land, so land always covers it.
        map.addLayer(
          {
            id: "frame",
            type: "raster",
            source: "frame",
            paint: { "raster-resampling": "nearest", "raster-fade-duration": 0 },
          },
          "land",
        );
      }
      shown = { spec, codes: loaded.codes };
      callbacks.current.onStatus("ready");
      callbacks.current.onFrameShown?.(spec.key);
      // Keep the reading in step with the frame: re-read the last tapped spot.
      if (lastTap) read(lastTap.lng, lastTap.lat, map.project([lastTap.lng, lastTap.lat]));
    }
    showRef.current = (spec) => void show(spec);

    function read(lng: number, lat: number, point: { x: number; y: number }) {
      // Ignore taps until a frame has loaded, so we never say "no data" by mistake.
      if (!map || !marker || !shown) return;
      lastTap = { lng, lat };
      marker.setLngLat([lng, lat]).addTo(map);
      const { spec, codes } = shown;
      const onLand = map.getLayer("land") && map.queryRenderedFeatures([point.x, point.y], { layers: ["land"] }).length > 0;
      const pixel = pixelAt(spec, lng, lat);
      const code = pixel ? codes[pixel.y * spec.width + pixel.x] : 0;
      let reading: Reading;
      if (onLand) reading = { kind: "land", lng, lat };
      else if (code === spec.encoding.nodata) reading = { kind: "nodata", lng, lat };
      else reading = { kind: "value", lng, lat, code };
      callbacks.current.onReading(reading);
    }

    start().catch((err) => {
      console.error("The map couldn't start:", err); // e.g. no WebGL
      if (!stopped) callbacks.current.onStatus("error");
    });

    return () => {
      stopped = true;
      showRef.current = () => {};
      marker?.remove();
      map?.remove();
      for (const loaded of cache.values()) loaded.then((l) => URL.revokeObjectURL(l.url), () => {});
    };
  }, []);

  return <div ref={containerRef} className="map" />;
}

/** Read the data PNG's raw values: one byte (0–255) per pixel. */
async function loadCodes(url: string, width: number, height: number): Promise<Uint8Array> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  // Turn off color management so every pixel keeps its exact number.
  const bitmap = await createImageBitmap(await response.blob(), {
    colorSpaceConversion: "none",
    premultiplyAlpha: "none",
  });
  if (bitmap.width !== width || bitmap.height !== height) {
    throw new Error(`The image size doesn't match its index file (${url})`);
  }
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("No 2D canvas");
  context.drawImage(bitmap, 0, 0);
  const rgba = context.getImageData(0, 0, width, height).data;
  const codes = new Uint8Array(width * height);
  for (let i = 0; i < codes.length; i++) codes[i] = rgba[i * 4]; // gray: R = G = B
  return codes;
}

/** Color the codes with the level scale and return a URL MapLibre can load. */
async function coloredImageUrl(codes: Uint8Array, spec: FrameSpec): Promise<string> {
  const canvas = document.createElement("canvas");
  canvas.width = spec.width;
  canvas.height = spec.height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("No 2D canvas");
  const pixels = colorize(codes, buildLut(spec.encoding));
  context.putImageData(new ImageData(new Uint8ClampedArray(pixels), spec.width, spec.height), 0, 0);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Couldn't make the colored image");
  return URL.createObjectURL(blob);
}

/** A 16 x 16 tile (8 x 8 on screen): ink with one faint diagonal paper line. */
function hatchPattern(): ImageData {
  const size = 16;
  const data = new Uint8ClampedArray(size * size * 4);
  const ink = [0x19, 0x1a, 0x18];
  const [pr, pg, pb, alpha] = HATCH_LINE;
  const line = [pr, pg, pb].map((c, k) => Math.round(ink[k] + (c - ink[k]) * alpha));
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const onLine = (x + y) % size < 2; // a 2-pixel (1 on screen) diagonal
      data.set([...(onLine ? line : ink), 255], (y * size + x) * 4);
    }
  }
  return new ImageData(data, size, size);
}
