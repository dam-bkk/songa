"use client";
import { events } from "@/lib/mockData";

export interface GameEvent {
  time: string;
  type: string;
  player: string;
  team: string;
  icon: string;
}

interface Props {
  events?: GameEvent[];
}

export function EventTimeline({ events: propEvents }: Props = {}) {
  const rows = propEvents ?? events;
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
      <p className="font-mono text-xs text-slate-400 uppercase tracking-wide mb-6">Actions clés détectées</p>
      <div className="flex flex-col gap-3">
        {rows.map((e, i) => (
          <div key={i} className="flex items-center gap-4 p-3 rounded-lg hover:bg-ink/50 transition-colors">
            <span className="font-mono text-xs text-slate-400 w-12 shrink-0">{e.time}</span>
            <div className="w-2 h-2 rounded-full bg-court shrink-0"/>
            <span className="font-geist text-sm text-bone">{e.type}</span>
            <span className="font-geist text-sm text-slate-400 ml-auto">{e.player}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
