"use client";
import { useLang } from "@/lib/i18n";
import { useDemoModal } from "@/lib/demoModal";
import { Logo } from "@/components/brand/Logo";
import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

export function Header() {
  const { lang, setLang, t } = useLang();
  const { open } = useDemoModal();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", h);
    return () => window.removeEventListener("scroll", h);
  }, []);

  const navLinks = [
    { href: "#product", label: t.nav.product },
    { href: "#how", label: t.nav.solutions },
    { href: "#pricing", label: t.pricing.label },
    { href: "#audience", label: t.nav.about },
  ];

  return (
    <>
      <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "bg-ink/90 backdrop-blur-md border-b border-slate-700" : ""}`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo className="h-10 w-auto text-bone" />

          <nav className="hidden md:flex items-center gap-8 text-sm font-geist text-slate-400">
            {navLinks.map(l => (
              <a key={l.href} href={l.href} className="hover:text-bone transition-colors">{l.label}</a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setLang(lang === "fr" ? "en" : "fr")}
              className="text-xs font-mono text-slate-400 hover:text-bone border border-slate-700 hover:border-slate-400 px-2 py-1 rounded transition-all"
            >
              {lang === "fr" ? "EN" : "FR"}
            </button>
            <a href="#" className="hidden md:block text-sm text-slate-400 hover:text-bone transition-colors">{t.nav.login}</a>
            <button onClick={open} className="hidden sm:block text-sm bg-court text-ink font-medium px-4 py-2 rounded hover:bg-court/90 transition-colors font-geist">
              {t.nav.demo}
            </button>
            <button
              onClick={() => setMobileOpen(v => !v)}
              className="md:hidden p-1 text-slate-400 hover:text-bone transition-colors"
              aria-label="Menu"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 bg-black/60 z-40 md:hidden"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              className="fixed top-16 left-0 right-0 z-50 bg-ink border-b border-slate-700 px-6 py-4 md:hidden"
              initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              <nav className="flex flex-col mb-4">
                {navLinks.map(l => (
                  <a
                    key={l.href} href={l.href}
                    className="font-geist text-base text-slate-400 hover:text-bone py-3 border-b border-slate-700/40 transition-colors last:border-0"
                    onClick={() => setMobileOpen(false)}
                  >
                    {l.label}
                  </a>
                ))}
              </nav>
              <button
                onClick={() => { open(); setMobileOpen(false); }}
                className="w-full text-sm bg-court text-ink font-medium py-3 rounded hover:bg-court/90 transition-colors font-geist"
              >
                {t.nav.demo}
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
