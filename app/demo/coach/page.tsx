"use client";
import { useLang } from "@/lib/i18n";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { CourtHeatmap } from "@/components/dashboard/CourtHeatmap";
import { PlayerTable } from "@/components/dashboard/PlayerTable";
import { EventTimeline } from "@/components/dashboard/EventTimeline";
import { Download } from "lucide-react";

export default function CoachPage() {
  const { t } = useLang();
  const c = t.coach;

  return (
    <DashboardLayout
      activeItem="match"
      title={c.title}
      subtitle={c.subtitle}
      actions={
        <button className="flex items-center gap-2 border border-slate-700 hover:border-slate-400 text-slate-400 hover:text-bone px-4 py-2 rounded text-sm font-geist transition-all">
          <Download size={14} /> {c.export}
        </button>
      }
    >
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {c.stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} />
        ))}
      </div>

      {/* Video + heatmap */}
      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden aspect-video flex items-center justify-center relative">
          <div className="absolute inset-0 bg-gradient-to-br from-slate-900 to-ink" />
          <div className="relative z-10 flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full border-2 border-court flex items-center justify-center">
              <div className="w-0 h-0 border-t-[10px] border-t-transparent border-b-[10px] border-b-transparent border-l-[18px] border-l-court ml-1" />
            </div>
            <p className="font-mono text-xs text-slate-400">
              ABC Fighters vs Étoile Filante · Q3
            </p>
          </div>
        </div>
        <CourtHeatmap />
      </div>

      <div className="space-y-6">
        <PlayerTable />
        <EventTimeline />
      </div>
    </DashboardLayout>
  );
}
