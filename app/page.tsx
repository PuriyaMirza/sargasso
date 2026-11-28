// The map page. latest.json and monthly.json are read when the site is built,
// so the data date is in the page itself. The daily data job commits new
// data, and Vercel rebuilds the site each time.
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { type Latest, type Monthly } from "@/lib/frame";
import NowView from "./now-view";

const DATA_DIR = path.join(process.cwd(), "public", "data");

// No try/catch on purpose: if latest.json is missing or broken, the build
// fails loudly and Vercel keeps serving the last good version of the site.
function readLatest(): Latest {
  return JSON.parse(readFileSync(path.join(DATA_DIR, "latest.json"), "utf8"));
}

// monthly.json is optional: without it, the History view is simply disabled.
// If it exists but is broken, the build fails, as above.
function readMonthly(): Monthly | null {
  const file = path.join(DATA_DIR, "monthly.json");
  return existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : null;
}

export default function Home() {
  return (
    <main className="now">
      <header className="now-head">
        <h1>Sargassum Map</h1>
        <p className="lede">
          A relative index of floating sargassum across the Caribbean, Gulf of Mexico and western
          Atlantic, from USF satellite data.
        </p>
      </header>
      <NowView latest={readLatest()} monthly={readMonthly()} />
    </main>
  );
}
