"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Download, ArrowLeft, AlertCircle } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { StatCard } from "@/components/dashboard/StatCard";
import { CourtHeatmap } from "@/components/dashboard/CourtHeatmap";
import { PlayerTable } from "@/components/dashboard/PlayerTable";
import { EventTimeline } from "@/components/dashboard/EventTimeline";
import { api, type MatchStats } from "@/lib/api";
import { type ShotZone } from "@/components/dashboard/CourtHeatmap";
import { type Player } from "@/components/dashboard/PlayerTable";
import { type GameEvent } from "@/components/dashboard/EventTimeline";

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-slate-900 rounded-xl animate-pulse ${className}`}
    />
  );
}

function SkeletonPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
      <Skeleton className="h-64" />
      <Skeleton className="h-48" />
    </div>
  );
}

// ─── Data mappers ─────────────────────────────────────────────────────────────

function mapShotChart(
  shotChart: MatchStats["shot_chart"],
): ShotZone[] {
  // Map API zones to SVG coordinates (same court layout as CourtHeatmap)
  const coordMap: Record<string, { x: number; y: number }> = {
    paint:        { x: 250, y: 280 },
    mid_left:     { x: 130, y: 220 },
    mid_right:    { x: 370, y: 220 },
    corner_left:  { x: 60,  y: 160 },
    corner_right: { x: 440, y: 160 },
    top_key:      { x: 250, y: 160 },
    arc_left:     { x: 100, y: 280 },
    arc_right:    { x: 400, y: 280 },
  };

  return Object.entries(shotChart).map(([zone, data], i) => ({
    zone,
    made: data.made,
    attempted: data.attempted,
    x: coordMap[zone]?.x ?? 150 + i * 40,
    y: coordMap[zone]?.y ?? 200,
  }));
}

function mapPlayers(
  playerStats: MatchStats["player_stats"],
): Player[] {
  return Object.entries(playerStats).map(([, p], i) => ({
    id: i + 1,
    name: p.name,
    pos: p.pos,
    pts: p.shots_made * 2,
    reb: 0,
    ast: 0,
    pm: p.shot_pct >= 0.5 ? `+${Math.round(p.shot_pct * 10)}` : `-${Math.round((1 - p.shot_pct) * 5)}`,
    age: 0,
    trend: [
      Math.round(p.avg_speed_ms * 10),
      Math.round(p.max_speed_ms * 8),
      Math.round(p.avg_speed_ms * 11),
      Math.round(p.shots_attempted),
      Math.round(p.shots_made * 2),
      Math.round(p.shot_pct * 100),
    ],
  }));
}

function mapEvents(
  keyEvents: MatchStats["key_events"],
): GameEvent[] {
  return keyEvents.map((e) => {
    const m = Math.floor(e.time_s / 60);
    const s = Math.floor(e.time_s % 60);
    return {
      time: `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`,
      type: e.type,
      player: e.player,
      team: "—",
      icon: e.type.toLowerCase().includes("tir") ? "three" : "steal",
    };
  });
}

function formatDuration(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const params = useParams();
  const jobId = typeof params.jobId === "string" ? params.jobId : "";

  const [stats, setStats] = useState<MatchStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    api
      .getResults(jobId)
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(
            err instanceof Error ? err.message : "Impossible de charger les résultats.",
          );
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // ── Computed stats cards ───────────────────────────────────────────────────

  const statCards = stats
    ? [
        {
          label: "Durée analysée",
          value: formatDuration(stats.meta.duration_s),
        },
        {
          label: "Joueurs trackés",
          value: String(Object.keys(stats.player_stats).length),
        },
        {
          label: "Events détectés",
          value: String(stats.key_events.length),
        },
        {
          label: "Efficacité off.",
          value: (() => {
            const totMade = Object.values(stats.player_stats).reduce(
              (s, p) => s + p.shots_made,
              0,
            );
            const totAtt = Object.values(stats.player_stats).reduce(
              (s, p) => s + p.shots_attempted,
              0,
            );
            return totAtt > 0
              ? `${Math.round((totMade / totAtt) * 100)}%`
              : "—";
          })(),
        },
      ]
    : [];

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-ink text-bone">
      {/* Header */}
      <header className="border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Logo className="h-6 w-auto text-bone" />
          <div>
            <a
              href="/upload"
              className="flex items-center gap-1.5 font-geist text-xs text-slate-400 hover:text-bone transition-colors"
            >
              <ArrowLeft size={12} />
              Nouveau match
            </a>
            {stats && (
              <>
                <h1 className="font-fraunces text-xl text-bone mt-0.5">
                  {stats.meta.game}
                </h1>
                <p className="font-mono text-xs text-slate-400">
                  {stats.meta.date} ·{" "}
                  {formatDuration(stats.meta.duration_s)} ·{" "}
                  {stats.meta.fps} fps
                </p>
              </>
            )}
          </div>
        </div>
        <a
          href={`/api/report?jobId=${jobId}`}
          className="flex items-center gap-2 border border-slate-700 hover:border-slate-400 text-slate-400 hover:text-bone px-4 py-2 rounded text-sm font-geist transition-all"
        >
          <Download size={14} />
          Export PDF
        </a>
      </header>

      {/* Body */}
      {isLoading && <SkeletonPage />}

      {error && !isLoading && (
        <div className="max-w-xl mx-auto px-6 py-16 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-red-900/20 flex items-center justify-center">
            <AlertCircle size={20} className="text-red-400" />
          </div>
          <p className="font-fraunces text-xl text-bone">
            Résultats introuvables
          </p>
          <p className="font-mono text-xs text-slate-400">{error}</p>
          <a
            href="/upload"
            className="mt-2 font-geist text-sm text-court hover:underline"
          >
            Retour à l&apos;upload
          </a>
        </div>
      )}

      {stats && !isLoading && (
        <motion.main
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="max-w-7xl mx-auto px-6 py-8 space-y-8"
        >
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {statCards.map((s) => (
              <StatCard key={s.label} label={s.label} value={s.value} />
            ))}
          </div>

          {/* Court + Players */}
          <div className="grid lg:grid-cols-2 gap-6">
            <CourtHeatmap data={mapShotChart(stats.shot_chart)} />
            <PlayerTable players={mapPlayers(stats.player_stats)} />
          </div>

          {/* Events */}
          <EventTimeline events={mapEvents(stats.key_events)} />
        </motion.main>
      )}
    </div>
  );
}
