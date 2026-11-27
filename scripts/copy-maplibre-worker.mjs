// Copies MapLibre's web worker into public/ so the browser can load it.
// MapLibre 6 looks for its worker file next to its own code, but Next.js moves
// that code when it bundles it, so app/sargassum-map.tsx points MapLibre at
// /maplibre/ instead. Runs automatically before `npm run dev` and `npm run build`.
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public/maplibre", { recursive: true });
copyFileSync(
  "node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs",
  "public/maplibre/maplibre-gl-worker.mjs",
);
console.log("Copied the MapLibre worker to public/maplibre/");
