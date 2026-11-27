// The "Now" view: this week's map. latest.json is read when the site is built,
// so the data date is in the page itself. The daily data job commits new
// data, and Vercel rebuilds the site each time.
import { readFileSync } from "node:fs";
import path from "node:path";

import { formatDataDate, type Latest } from "@/lib/frame";
import NowView from "./now-view";

// No try/catch on purpose: if latest.json is missing or broken, the build
// fails loudly and Vercel keeps serving the last good version of the site.
function readLatest(): Latest {
  const file = path.join(process.cwd(), "public", "data", "latest.json");
  return JSON.parse(readFileSync(file, "utf8"));
}

export default function Home() {
  const latest = readLatest();
  return (
    <main className="now">
      <header className="now-head">
        <h1>Sargassum Map</h1>
        <p className="lede">
          A relative index of floating sargassum across the Caribbean, Gulf of Mexico and western
          Atlantic, from USF satellite data.
        </p>
        <div className="date-block">
          <p className="cap label">Data date</p>
          <p className="date">
            <time dateTime={latest.data_date}>{formatDataDate(latest.data_date)}</time>
          </p>
          <p className="sub">7-day composite</p>
        </div>
      </header>
      <NowView latest={latest} />
    </main>
  );
}
