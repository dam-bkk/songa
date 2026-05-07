"use client";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { CheckCircle, ArrowRight, Sparkles } from "lucide-react";
import { useLang } from "@/lib/i18n";

// ─── Mini Shot Chart ────────────────────────────────────────────────────────

function MiniShotChart() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });

  const zones = [
    { id: "paint",       x: 172, y: 148, r: 28, pct: "64%", made: 18, color: "#0055FF", opacity: 0.35 },
    { id: "mid_left",    x: 92,  y: 118, r: 18, pct: "40%", made: 4,  color: "#CCFF00", opacity: 0.28 },
    { id: "mid_right",   x: 256, y: 118, r: 18, pct: "45%", made: 5,  color: "#CCFF00", opacity: 0.28 },
    { id: "corner_left", x: 34,  y: 82,  r: 15, pct: "43%", made: 3,  color: "#9A9389", opacity: 0.22 },
    { id: "corner_right",x: 316, y: 82,  r: 15, pct: "50%", made: 4,  color: "#0055FF", opacity: 0.25 },
    { id: "top_key",     x: 174, y: 75,  r: 20, pct: "40%", made: 6,  color: "#CCFF00", opacity: 0.25 },
    { id: "arc_left",    x: 60,  y: 148, r: 16, pct: "33%", made: 3,  color: "#9A9389", opacity: 0.2  },
    { id: "arc_right",   x: 290, y: 148, r: 16, pct: "40%", made: 4,  color: "#CCFF00", opacity: 0.22 },
  ];

  const traces = [
    { d: "M 60 175 C 80 155 120 140 172 148", color: "#CCFF00", delay: 0.3 },
    { d: "M 174 75 C 174 100 172 120 172 148", color: "#0055FF", delay: 0.7 },
    { d: "M 256 118 C 230 130 205 138 172 148", color: "#CCFF00", delay: 1.0 },
    { d: "M 316 82 Q 290 110 256 118",          color: "#9A9389", delay: 1.3 },
  ];

  return (
    <div ref={ref} className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono text-xs text-slate-400">Shot Chart · Q3</span>
        <span className="font-mono text-xs text-signal bg-signal/10 px-2 py-0.5 rounded-full flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-signal rounded-full animate-pulse" />
          LIVE
        </span>
      </div>

      {/* SVG court — top-down half court */}
      <svg viewBox="0 0 350 210" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
        {/* Court background */}
        <rect x="0" y="0" width="350" height="210" rx="4" fill="#1A1815" />
        {/* Baseline */}
        <line x1="10" y1="200" x2="340" y2="200" stroke="#3A3631" strokeWidth="1.2" />
        {/* Sidelines */}
        <line x1="10" y1="10" x2="10" y2="200" stroke="#3A3631" strokeWidth="1.2" />
        <line x1="340" y1="10" x2="340" y2="200" stroke="#3A3631" strokeWidth="1.2" />
        {/* Paint / key */}
        <rect x="112" y="150" width="122" height="50" stroke="#3A3631" strokeWidth="1.2" fill="none" />
        {/* Free throw circle */}
        <path d="M 112 150 Q 173 120 234 150" stroke="#3A3631" strokeWidth="1" strokeDasharray="3 3" fill="none" />
        {/* Restricted area */}
        <path d="M 148 200 Q 175 180 202 200" stroke="#3A3631" strokeWidth="1" fill="none" />
        {/* Backboard */}
        <line x1="155" y1="203" x2="195" y2="203" stroke="#9A9389" strokeWidth="2" />
        {/* Basket */}
        <circle cx="175" cy="200" r="7" stroke="#9A9389" strokeWidth="1.2" fill="none" />
        {/* 3pt arc */}
        <path d="M 10 95 Q 175 -30 340 95" stroke="#3A3631" strokeWidth="1.2" fill="none" />
        {/* Corner 3 lines */}
        <line x1="10" y1="95" x2="10" y2="200" stroke="#3A3631" strokeWidth="1.2" />
        <line x1="340" y1="95" x2="340" y2="200" stroke="#3A3631" strokeWidth="1.2" />

        {/* Zone blobs */}
        {zones.map((z) => (
          <motion.circle
            key={z.id}
            cx={z.x} cy={z.y} r={z.r}
            fill={z.color}
            fillOpacity={inView ? z.opacity : 0}
            initial={{ fillOpacity: 0, r: z.r * 0.3 }}
            animate={inView ? { fillOpacity: z.opacity, r: z.r } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          />
        ))}

        {/* Zone % labels */}
        {zones.slice(0, 6).map((z) => (
          <motion.text
            key={`label-${z.id}`}
            x={z.x} y={z.y + 4}
            textAnchor="middle"
            fill="#F2EDE3"
            fontSize="8"
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 0.9 } : {}}
            transition={{ duration: 0.4, delay: 0.5 }}
          >
            {z.pct}
          </motion.text>
        ))}

        {/* Animated shot traces */}
        {traces.map((tr, i) => (
          <motion.path
            key={i}
            d={tr.d}
            stroke={tr.color}
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={inView ? { pathLength: 1, opacity: 0.6 } : {}}
            transition={{ duration: 1, delay: tr.delay, ease: "easeOut" }}
          />
        ))}

        {/* Animated shot arc (ball) */}
        <motion.path
          d="M 174 75 Q 140 30 175 200"
          stroke="#F2EDE3"
          strokeWidth="1"
          strokeDasharray="4 3"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={inView ? { pathLength: 1, opacity: 0.3 } : {}}
          transition={{ duration: 1.5, delay: 0.8, ease: "easeOut" }}
        />
      </svg>

      {/* Mini stats */}
      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-700">
        <div className="text-center">
          <p className="font-mono text-lg text-bone">78</p>
          <p className="font-mono text-xs text-slate-400">PTS</p>
        </div>
        <div className="text-center border-x border-slate-700">
          <p className="font-mono text-lg text-court">51%</p>
          <p className="font-mono text-xs text-slate-400">FG%</p>
        </div>
        <div className="text-center">
          <p className="font-mono text-lg text-signal">38%</p>
          <p className="font-mono text-xs text-slate-400">3P%</p>
        </div>
      </div>
    </div>
  );
}

// ─── Mini Trajectory Map ─────────────────────────────────────────────────────

function MiniTrajectoryMap() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });

  const playersA = [
    { id: "#7",  cx: 90,  cy: 80,  color: "#CCFF00" },
    { id: "#11", cx: 155, cy: 55,  color: "#CCFF00" },
    { id: "#3",  cx: 220, cy: 100, color: "#CCFF00" },
  ];
  const playersB = [
    { id: "#4",  cx: 125, cy: 130, color: "#0055FF" },
    { id: "#9",  cx: 190, cy: 145, color: "#0055FF" },
  ];

  const trajectories = [
    { d: "M 90 80 C 105 90 115 108 125 130",   color: "#CCFF00", delay: 0.4 },
    { d: "M 155 55 C 160 85 155 108 155 130",  color: "#CCFF00", delay: 0.7 },
    { d: "M 220 100 C 210 115 200 130 190 145",color: "#CCFF00", delay: 1.0 },
    { d: "M 125 130 C 140 120 160 118 190 118",color: "#0055FF", delay: 1.2 },
  ];

  return (
    <div ref={ref} className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono text-xs text-slate-400">Trajectory Map · Live</span>
        <span className="font-mono text-xs text-signal bg-signal/10 px-2 py-0.5 rounded-full flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-signal rounded-full animate-pulse" />
          30 fps
        </span>
      </div>

      {/* SVG court top-down */}
      <div className="relative">
        <svg viewBox="0 0 350 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
          <rect x="0" y="0" width="350" height="200" rx="4" fill="#1A1815" />
          {/* Court outline */}
          <rect x="10" y="10" width="330" height="180" rx="3" stroke="#3A3631" strokeWidth="1.2" fill="none" />
          {/* Center line */}
          <line x1="175" y1="10" x2="175" y2="190" stroke="#3A3631" strokeWidth="1" strokeDasharray="4 4" />
          {/* Center circle */}
          <circle cx="175" cy="100" r="30" stroke="#3A3631" strokeWidth="1" fill="none" />
          {/* Left paint */}
          <rect x="10" y="60" width="75" height="80" stroke="#3A3631" strokeWidth="1.2" fill="none" />
          {/* Left basket */}
          <circle cx="35" cy="100" r="8" stroke="#3A3631" strokeWidth="1" fill="none" />
          {/* Left 3pt */}
          <path d="M 10 42 Q 120 100 10 158" stroke="#3A3631" strokeWidth="1" fill="none" />
          {/* Right paint */}
          <rect x="265" y="60" width="75" height="80" stroke="#3A3631" strokeWidth="1.2" fill="none" />
          {/* Right basket */}
          <circle cx="315" cy="100" r="8" stroke="#3A3631" strokeWidth="1" fill="none" />
          {/* Right 3pt */}
          <path d="M 340 42 Q 230 100 340 158" stroke="#3A3631" strokeWidth="1" fill="none" />

          {/* Trajectory lines */}
          {trajectories.map((tr, i) => (
            <motion.path
              key={i}
              d={tr.d}
              stroke={tr.color}
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={inView ? { pathLength: 1, opacity: 0.65 } : {}}
              transition={{ duration: 1.2, delay: tr.delay, ease: "easeOut" }}
            />
          ))}

          {/* Team A dots */}
          {playersA.map((p, i) => (
            <motion.g key={p.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={inView ? { opacity: 1, scale: 1 } : {}}
              transition={{ delay: 0.2 + i * 0.15 }}
            >
              <circle cx={p.cx} cy={p.cy} r="9" fill={p.color} fillOpacity="0.2" />
              <circle cx={p.cx} cy={p.cy} r="5" fill={p.color} />
              <text x={p.cx} y={p.cy - 12} textAnchor="middle" fill={p.color} fontSize="7" fontFamily="monospace">{p.id}</text>
            </motion.g>
          ))}

          {/* Team B dots */}
          {playersB.map((p, i) => (
            <motion.g key={p.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={inView ? { opacity: 1, scale: 1 } : {}}
              transition={{ delay: 0.4 + i * 0.15 }}
            >
              <circle cx={p.cx} cy={p.cy} r="9" fill={p.color} fillOpacity="0.15" />
              <circle cx={p.cx} cy={p.cy} r="5" fill={p.color} />
              <text x={p.cx} y={p.cy - 12} textAnchor="middle" fill={p.color} fontSize="7" fontFamily="monospace">{p.id}</text>
            </motion.g>
          ))}
        </svg>

        {/* Floating info panel */}
        <motion.div
          className="absolute bottom-2 left-2 bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 backdrop-blur-sm"
          initial={{ opacity: 0, y: 8 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 1.6, duration: 0.4 }}
        >
          <p className="font-mono text-xs text-court font-semibold">Yao Konaté #7</p>
          <p className="font-mono text-xs text-slate-400">4.8 km · 7.4 m/s max</p>
        </motion.div>
      </div>

      {/* Team legend */}
      <div className="flex items-center gap-6 mt-3 pt-3 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-court" />
          <span className="font-mono text-xs text-slate-400">ABC Fighters</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-signal" />
          <span className="font-mono text-xs text-slate-400">Étoile du Sahel</span>
        </div>
        <div className="ml-auto font-mono text-xs text-slate-400">5 joueurs tracés</div>
      </div>
    </div>
  );
}

// ─── Mini Academy Roster ─────────────────────────────────────────────────────

function Sparkline({ values, color }: { values: number[]; color: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 52;
  const h = 20;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  });
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-13 h-5" style={{ width: 52, height: 20 }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const rosterData = [
  { initials: "FC", name: "Fatim Coulibaly",  age: "U18", pos: "PG", stat: "19.4 pts/j", trend: "+18%", positive: true,  sparkline: [14, 15, 16, 17, 18, 19] },
  { initials: "LD", name: "Lamine Diallo",    age: "U20", pos: "C",  stat: "12.1 reb/j", trend: "+12%", positive: true,  sparkline: [8, 9, 10, 10, 11, 12]  },
  { initials: "AS", name: "Aminata Sanogo",   age: "U16", pos: "SF", stat: "14.7 pts/j", trend: "+9%",  positive: true,  sparkline: [11, 12, 13, 13, 14, 15] },
  { initials: "KA", name: "Koffi Asante",     age: "U16", pos: "PG", stat: "16.8 pts/j", trend: "+22%", positive: true,  sparkline: [10, 12, 13, 14, 16, 17] },
];

function MiniAcademyRoster() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <div ref={ref} className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-court" />
          <span className="font-mono text-xs text-bone font-semibold">Talents émergents</span>
        </div>
        <span className="font-mono text-xs text-signal bg-signal/10 px-2 py-0.5 rounded-full">
          6 nouveaux ce mois
        </span>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[1fr_auto_auto_auto] gap-3 px-2 mb-2">
        <span className="font-mono text-xs text-slate-400">Joueur</span>
        <span className="font-mono text-xs text-slate-400 text-right">Stat</span>
        <span className="font-mono text-xs text-slate-400 text-right">Courbe</span>
        <span className="font-mono text-xs text-slate-400 text-right">Prog.</span>
      </div>

      {/* Player rows */}
      <div className="space-y-1">
        {rosterData.map((p, i) => (
          <motion.div
            key={p.name}
            className="grid grid-cols-[1fr_auto_auto_auto] gap-3 items-center bg-slate-900 hover:bg-slate-700/30 transition-colors rounded-lg px-2 py-2 border border-slate-700/50"
            initial={{ opacity: 0, x: 16 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2 + i * 0.1, duration: 0.4 }}
          >
            {/* Avatar + name */}
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-court/20 border border-court/30 flex items-center justify-center shrink-0">
                <span className="font-mono text-xs text-court font-semibold">{p.initials}</span>
              </div>
              <div className="min-w-0">
                <p className="font-geist text-xs text-bone truncate leading-tight">{p.name}</p>
                <p className="font-mono text-xs text-slate-400">{p.age} · {p.pos}</p>
              </div>
            </div>
            {/* Main stat */}
            <span className="font-mono text-xs text-slate-400 text-right whitespace-nowrap">{p.stat}</span>
            {/* Sparkline */}
            <div className="flex justify-end">
              <Sparkline values={p.sparkline} color={p.positive ? "#0055FF" : "#9A9389"} />
            </div>
            {/* Trend badge */}
            <span className={`font-mono text-xs px-1.5 py-0.5 rounded text-right whitespace-nowrap ${p.positive ? "text-signal bg-signal/10" : "text-slate-400 bg-slate-700/40"}`}>
              {p.trend}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-slate-700 flex items-center justify-between">
        <span className="font-mono text-xs text-slate-400">47 joueurs suivis · Saison 2025–26</span>
        <span className="font-mono text-xs text-court">Voir tous →</span>
      </div>
    </div>
  );
}

// ─── ShowcaseBlock ────────────────────────────────────────────────────────────

interface ShowcaseBlockProps {
  eyebrow: string;
  title: string;
  body: string;
  bullets: readonly string[];
  ctaText?: string;
  ctaHref?: string;
  mockup: React.ReactNode;
  reverse?: boolean;
}

function ShowcaseBlock({ eyebrow, title, body, bullets, ctaText, ctaHref, mockup, reverse = false }: ShowcaseBlockProps) {
  return (
    <motion.div
      className={`flex flex-col ${reverse ? "lg:flex-row-reverse" : "lg:flex-row"} gap-12 lg:gap-20 items-center mb-24 last:mb-0`}
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7 }}
      viewport={{ once: true, amount: 0.15 }}
    >
      {/* Text column */}
      <div className="flex-1 max-w-md">
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{eyebrow}</p>
        <h3 className="font-fraunces text-3xl lg:text-4xl text-bone mb-6 whitespace-pre-line leading-snug">{title}</h3>
        <p className="font-geist text-slate-400 leading-relaxed mb-8">{body}</p>
        <ul className="space-y-3 mb-8">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-3 font-geist text-sm text-slate-400">
              <CheckCircle size={16} className="text-signal mt-0.5 shrink-0" />
              {b}
            </li>
          ))}
        </ul>
        {ctaText && ctaHref && (
          <a
            href={ctaHref}
            className="inline-flex items-center gap-2 text-sm font-geist text-court hover:text-court/80 transition-colors"
          >
            {ctaText} <ArrowRight size={14} />
          </a>
        )}
      </div>

      {/* Mockup column */}
      <div className="flex-1 w-full max-w-xl">
        {mockup}
      </div>
    </motion.div>
  );
}

// ─── ProductShowcase ──────────────────────────────────────────────────────────

export function ProductShowcase() {
  const { t } = useLang();
  const sc = t.showcase;

  return (
    <section id="product" className="py-24 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="mb-20"
        >
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{sc.label}</p>
          <h2 className="font-fraunces text-4xl lg:text-5xl text-bone">{sc.headline}</h2>
        </motion.div>

        {/* Block 1 — Shot analysis (text left, mock right) */}
        <ShowcaseBlock
          eyebrow={sc.blocks[0].eyebrow}
          title={sc.blocks[0].title}
          body={sc.blocks[0].body}
          bullets={sc.blocks[0].bullets}
          ctaText={sc.blocks[0].cta}
          ctaHref="/demo/coach"
          mockup={<MiniShotChart />}
          reverse={false}
        />

        {/* Block 2 — Trajectory tracking (mock left, text right) */}
        <ShowcaseBlock
          eyebrow={sc.blocks[1].eyebrow}
          title={sc.blocks[1].title}
          body={sc.blocks[1].body}
          bullets={sc.blocks[1].bullets}
          mockup={<MiniTrajectoryMap />}
          reverse={true}
        />

        {/* Block 3 — Academy management (text left, mock right) */}
        <ShowcaseBlock
          eyebrow={sc.blocks[2].eyebrow}
          title={sc.blocks[2].title}
          body={sc.blocks[2].body}
          bullets={sc.blocks[2].bullets}
          mockup={<MiniAcademyRoster />}
          reverse={false}
        />
      </div>
    </section>
  );
}
