"use client";
import { useLang } from "@/lib/i18n";
import { Logo } from "@/components/brand/Logo";

export function Footer() {
  const { lang, setLang, t } = useLang();
  return (
    <footer className="border-t border-slate-700 py-12 md:py-16 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Brand row — full width on mobile */}
        <div className="mb-10 md:mb-12">
          <Logo className="h-10 w-auto text-bone mb-3" />
          <p className="font-geist text-sm text-slate-400 max-w-xs">{t.footer.tagline}</p>
        </div>

        {/* Link columns — 2 cols mobile, 3 cols md+ */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 mb-10 md:mb-12">
          {[
            { label: t.footer.product, links: t.footer.links_product },
            { label: t.footer.company, links: t.footer.links_company },
            { label: t.footer.legal, links: t.footer.links_legal },
          ].map((col, i) => (
            <div key={i}>
              <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{col.label}</p>
              <ul className="space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="font-geist text-sm text-slate-400 hover:text-bone transition-colors">{l}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-6 border-t border-slate-700">
          <p className="font-mono text-xs text-slate-400">{t.footer.origin}</p>
          <button
            onClick={() => setLang(lang === "fr" ? "en" : "fr")}
            className="font-mono text-xs text-slate-400 hover:text-bone border border-slate-700 hover:border-slate-400 px-2 py-1 rounded transition-all"
          >
            {lang === "fr" ? "EN" : "FR"}
          </button>
        </div>
      </div>
    </footer>
  );
}
