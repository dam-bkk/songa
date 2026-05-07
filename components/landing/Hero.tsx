"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";
import { MapPin } from "lucide-react";

function CourtSVG() {
  return (
    <div className="relative w-full aspect-[4/3] max-w-lg mx-auto">
      <svg viewBox="0 0 500 375" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        {/* Court outline */}
        <rect x="20" y="20" width="460" height="335" rx="4" stroke="#3A3631" strokeWidth="1.5" fill="#1A1815"/>
        {/* Center line */}
        <line x1="250" y1="20" x2="250" y2="355" stroke="#3A3631" strokeWidth="1" strokeDasharray="4 4"/>
        {/* Center circle */}
        <circle cx="250" cy="187" r="40" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        {/* Left paint */}
        <rect x="20" y="130" width="120" height="115" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        {/* Left basket */}
        <circle cx="60" cy="187" r="12" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        <line x1="20" y1="187" x2="72" y2="187" stroke="#3A3631" strokeWidth="1.5"/>
        {/* Left 3pt arc */}
        <path d="M 20 80 Q 180 187 20 294" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        {/* Right paint */}
        <rect x="360" y="130" width="120" height="115" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        {/* Right basket */}
        <circle cx="440" cy="187" r="12" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
        <line x1="428" y1="187" x2="480" y2="187" stroke="#3A3631" strokeWidth="1.5"/>
        {/* Right 3pt arc */}
        <path d="M 480 80 Q 320 187 480 294" stroke="#3A3631" strokeWidth="1.5" fill="none"/>

        {/* Animated player trajectory traces */}
        <motion.path
          d="M 80 187 C 120 150 180 160 220 140 C 260 120 300 130 340 160"
          stroke="#CCFF00" strokeWidth="1.5" fill="none" strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.7 }}
          transition={{ duration: 2, delay: 0.3, ease: "easeOut" }}
        />
        <motion.path
          d="M 250 300 C 240 260 260 220 250 187"
          stroke="#0055FF" strokeWidth="1.5" fill="none" strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.8 }}
          transition={{ duration: 1.5, delay: 0.8, ease: "easeOut" }}
        />
        <motion.path
          d="M 340 160 C 380 140 420 150 440 187"
          stroke="#CCFF00" strokeWidth="1.5" fill="none" strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ duration: 1.5, delay: 1.5, ease: "easeOut" }}
        />
        {/* Ball arc */}
        <motion.path
          d="M 340 160 Q 400 80 440 187"
          stroke="#F2EDE3" strokeWidth="1" strokeDasharray="4 3" fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.4 }}
          transition={{ duration: 2, delay: 2, ease: "easeOut" }}
        />

        {/* Player dots */}
        {[
          { cx: 80, cy: 187, delay: 0.2, color: "#CCFF00" },
          { cx: 220, cy: 140, delay: 0.5, color: "#CCFF00" },
          { cx: 250, cy: 300, delay: 0.7, color: "#0055FF" },
          { cx: 340, cy: 160, delay: 1.2, color: "#CCFF00" },
          { cx: 180, cy: 220, delay: 0.9, color: "#9A9389" },
        ].map((dot, i) => (
          <motion.circle
            key={i} cx={dot.cx} cy={dot.cy} r="5"
            fill={dot.color}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: [0, 1, 0.7, 1], scale: 1 }}
            transition={{ delay: dot.delay, duration: 0.4, opacity: { duration: 2, repeat: Infinity, repeatDelay: 1 } }}
          />
        ))}
      </svg>
      {/* Glow effect */}
      <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-transparent pointer-events-none" />
    </div>
  );
}

export function Hero() {
  const { t } = useLang();
  return (
    <section className="min-h-screen flex items-center pt-16 px-6">
      <div className="max-w-7xl mx-auto w-full grid lg:grid-cols-[3fr_2fr] gap-12 lg:gap-20 items-center py-20">
        <div>
          <motion.p
            className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-6"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          >
            {t.hero.eyebrow}
          </motion.p>
          <motion.h1
            className="font-fraunces text-4xl md:text-5xl lg:text-7xl font-light leading-[1.05] tracking-tight text-bone mb-6 whitespace-pre-line"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
          >
            {t.hero.headline}
          </motion.h1>
          <motion.p
            className="font-geist text-lg text-slate-400 leading-relaxed max-w-xl mb-10"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
          >
            {t.hero.sub}
          </motion.p>
          <motion.div
            className="flex flex-wrap gap-4 mb-12"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.3 }}
          >
            <a href="#" className="bg-court text-ink font-geist font-medium px-6 py-3 rounded hover:bg-court/90 transition-colors text-sm">
              {t.hero.cta_primary}
            </a>
            <a href="/demo/coach" className="border border-slate-700 text-bone font-geist px-6 py-3 rounded hover:border-slate-400 transition-colors text-sm">
              {t.hero.cta_secondary}
            </a>
          </motion.div>
          <motion.div
            className="flex items-center gap-2 text-xs font-mono text-slate-400"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          >
            <MapPin size={12} className="text-court" />
            {t.hero.origin}
          </motion.div>
        </div>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, delay: 0.2 }}
        >
          <CourtSVG />
        </motion.div>
      </div>
    </section>
  );
}
