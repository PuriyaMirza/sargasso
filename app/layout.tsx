import type { Metadata, Viewport } from "next";
import { Cormorant, Jost } from "next/font/google";
import ColumnField from "./column-field";
import "./globals.css";

// next/font downloads these from Google Fonts at build time and serves them
// from our own site, so visitors' browsers never contact Google.
const cormorant = Cormorant({
  subsets: ["latin"],
  weight: "300",
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});
const jost = Jost({
  subsets: ["latin"],
  weight: ["300", "400"],
  variable: "--font-jost",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sargassum Map",
  description:
    "A free map of sargassum levels across the Caribbean, Gulf of Mexico and western Atlantic, from USF satellite data.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  colorScheme: "dark",
  themeColor: "#191a18",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${cormorant.variable} ${jost.variable}`}>
      <body>
        <ColumnField />
        <div className="frame">
          {children}
          <footer className="foot">
            <p>
              Data: USF Optical Oceanography Lab, College of Marine Science, via NOAA AOML
              CoastWatch/OceanWatch ERDDAP. Experimental; may contain inaccuracies; not for
              navigation or legal use. Basemap: Made with Natural Earth.
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
