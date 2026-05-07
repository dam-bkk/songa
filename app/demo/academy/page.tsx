"use client";
import { useLang } from "@/lib/i18n";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { academyPlayers, progressionData } from "@/lib/mockData";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Sparkles, Upload } from "lucide-react";

export default function AcademyPage() {
  const { t } = useLang();
  const a = t.academy;

  return (
    <DashboardLayout
      activeItem="academy"
      title={a.title}
      subtitle={a.subtitle}
      actions={
        <a
          href="/upload"
          className="flex items-center gap-2 border border-slate-700 hover:border-slate-400 text-slate-400 hover:text-bone px-4 py-2 rounded text-sm font-geist transition-all"
        >
          <Upload size={14} /> Ajouter une vidéo
        </a>
      }
    >
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {a.stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} />
        ))}
      </div>

      {/* Roster grid */}
      <div className="mb-8">
        <p className="font-mono text-xs text-slate-400 uppercase tracking-wide mb-4">
          Effectif
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {academyPlayers.map((p) => (
            <div
              key={p.id}
              className="bg-slate-900 border border-slate-700 rounded-xl p-5 hover:border-slate-400 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-fraunces text-lg text-bone">{p.name}</p>
                  <p className="font-mono text-xs text-slate-400">
                    {p.age} · {p.pos}
                  </p>
                </div>
                {p.emerging && (
                  <Sparkles size={14} className="text-court mt-1 shrink-0" />
                )}
              </div>
              <p className="font-mono text-xl text-bone mb-1">{p.stat}</p>
              <p className="font-geist text-xs text-slate-400">{p.note}</p>
              <div
                className={`mt-3 inline-block font-mono text-xs px-2 py-0.5 rounded ${
                  p.trend.startsWith("+")
                    ? "text-signal bg-signal/10"
                    : "text-slate-400 bg-slate-700/30"
                }`}
              >
                {p.trend}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Progression chart */}
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 mb-8">
        <p className="font-mono text-xs text-slate-400 uppercase tracking-wide mb-6">
          Progression collective
        </p>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart
            data={progressionData}
            margin={{ top: 0, right: 0, bottom: 0, left: -20 }}
          >
            <XAxis
              dataKey="month"
              tick={{
                fontSize: 11,
                fill: "#9A9389",
                fontFamily: "var(--font-jetbrains-var)",
              }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{
                fontSize: 11,
                fill: "#9A9389",
                fontFamily: "var(--font-jetbrains-var)",
              }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1A1815",
                border: "1px solid #3A3631",
                borderRadius: 8,
                fontFamily: "var(--font-jetbrains-var)",
                fontSize: 12,
                color: "#F2EDE3",
              }}
              itemStyle={{ color: "#F2EDE3" }}
            />
            <Line
              type="monotone"
              dataKey="offRating"
              stroke="#CCFF00"
              strokeWidth={2}
              dot={false}
              name="Off. Rating"
            />
            <Line
              type="monotone"
              dataKey="defRating"
              stroke="#0055FF"
              strokeWidth={2}
              dot={false}
              name="Def. Rating"
            />
            <Line
              type="monotone"
              dataKey="pace"
              stroke="#9A9389"
              strokeWidth={1.5}
              dot={false}
              name="Pace"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Talents émergents */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={14} className="text-court" />
          <p className="font-mono text-xs text-slate-400 uppercase tracking-wide">
            Talents émergents
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {academyPlayers
            .filter((p) => p.emerging)
            .slice(0, 3)
            .map((p) => (
              <div
                key={p.id}
                className="bg-slate-900 border border-court/30 rounded-xl p-6"
              >
                <p className="font-fraunces text-xl text-bone mb-1">{p.name}</p>
                <p className="font-mono text-xs text-slate-400 mb-4">
                  {p.age} · {p.pos}
                </p>
                <p className="font-mono text-2xl text-signal mb-2">{p.trend}</p>
                <p className="font-geist text-sm text-slate-400">{p.note}</p>
              </div>
            ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
