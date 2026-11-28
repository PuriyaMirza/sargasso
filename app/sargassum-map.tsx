"use client";

// The map: MapLibre with no outside tiles. Layers, bottom to top:
//   ocean (ink) → no-data hatch → today's frame → land → coastline.
// The frame is a grayscale "data PNG"; we color it here with the lookup
// table from lib/frame.ts and hand MapLibre the colored copy.

import "maplibre-gl/dist/maplibre-gl.css";

import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import { useEffect, useRef } from "react";

import { buildLut, colorize, pixelAt, type Latest } from "@/lib/frame";

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
  latest: Latest;
  onReading: (reading: Reading) => void;
  onStatus: (status: MapStatus) => void;
};

export default function SargassumMap({ latest, onReading, onStatus }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Keep the newest callbacks without re-creating the map when they change.
  const callbacks = useRef({ onReading, onStatus });
  useEffect(() => {
    callbacks.current = { onReading, onStatus };
  });

  useEffect(() => {
    let map: MapLibreMap | undefined;
    let marker: Marker | undefined;
    let frameUrl: string | undefined;
    let codes: Uint8Array | undefined; // the frame's raw values, once loaded
    let frameReady = false;
    let stopped = false; // set when the component unmounts
    const { west, south, east, north } = latest.bounds;

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

        try {
          codes = await loadCodes(`/data/${latest.image}`, latest.width, latest.height);
          frameUrl = await coloredImageUrl(codes, latest);
        } catch (err) {
          console.error("Couldn't load the latest frame:", err);
          if (!stopped) callbacks.current.onStatus("error");
          return;
        }
        if (stopped || !map) return;
        map.addSource("frame", {
          type: "image",
          url: frameUrl,
          coordinates: [[west, north], [east, north], [east, south], [west, south]],
        });
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
        frameReady = true;
        callbacks.current.onStatus("ready");
      });

      // Log every map error. Only show the "couldn't load" message if the
      // frame isn't up yet; a later hiccup shouldn't hide a working map.
      map.on("error", (event) => {
        console.error("Map error:", event.error ?? event);
        if (!stopped && !frameReady) callbacks.current.onStatus("error");
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

    function read(lng: number, lat: number, point: { x: number; y: number }) {
      // Ignore taps until the frame has loaded, so we never say "no data" by mistake.
      if (!map || !marker || !codes || !frameReady) return;
      marker.setLngLat([lng, lat]).addTo(map);
      const onLand = map.getLayer("land") && map.queryRenderedFeatures([point.x, point.y], { layers: ["land"] }).length > 0;
      const pixel = pixelAt(latest, lng, lat);
      let reading: Reading;
      if (onLand) reading = { kind: "land", lng, lat };
      else if (!pixel || codes[pixel.y * latest.width + pixel.x] === 0) reading = { kind: "nodata", lng, lat };
      else reading = { kind: "value", lng, lat, code: codes[pixel.y * latest.width + pixel.x] };
      callbacks.current.onReading(reading);
    }

    start().catch((err) => {
      console.error("The map couldn't start:", err); // e.g. no WebGL
      if (!stopped) callbacks.current.onStatus("error");
    });

    return () => {
      stopped = true;
      marker?.remove();
      map?.remove();
      if (frameUrl) URL.revokeObjectURL(frameUrl);
    };
  }, [latest]);

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
    throw new Error("The image size doesn't match latest.json");
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
async function coloredImageUrl(codes: Uint8Array, latest: Latest): Promise<string> {
  const canvas = document.createElement("canvas");
  canvas.width = latest.width;
  canvas.height = latest.height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("No 2D canvas");
  const pixels = colorize(codes, buildLut(latest.encoding));
  context.putImageData(new ImageData(new Uint8ClampedArray(pixels), latest.width, latest.height), 0, 0);
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
