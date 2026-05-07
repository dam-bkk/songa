import type { Metadata } from "next";
import { Fraunces, Geist, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { LangProvider } from "@/lib/i18n";
import { ThemeProvider } from "@/lib/theme";
import { DemoModalProvider } from "@/lib/demoModal";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces-var", weight: "variable", axes: ["opsz","SOFT"] });
const geist = Geist({ subsets: ["latin"], variable: "--font-geist-var" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-var", weight: ["400","500"] });

export const metadata: Metadata = {
  title: "Songa — Computer Vision for African Basketball",
  description: "Songa analyzes basketball games with computer vision for coaches and academies across Africa.",
  keywords: ["basketball analytics", "computer vision", "African basketball", "coach dashboard", "basketball AI", "Côte d'Ivoire"],
  openGraph: { title: "Songa — Computer Vision for African Basketball", type: "website", locale: "fr_FR", alternateLocale: "en_US" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark scroll-smooth">
      <body className={`${fraunces.variable} ${geist.variable} ${jetbrains.variable} antialiased bg-ink text-bone`}>
        <ThemeProvider><LangProvider><DemoModalProvider>{children}</DemoModalProvider></LangProvider></ThemeProvider>
      </body>
    </html>
  );
}
