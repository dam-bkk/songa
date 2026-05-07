"use client";
import { players } from "@/lib/mockData";

export interface Player {
  id: number;
  name: string;
  pos: string;
  pts: number;
  reb: number;
  ast: number;
  pm: string;
  age: number;
  trend: number[];
}

interface Props {
  players?: Player[];
}

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data), min = Math.min(...data);
  const w = 60, h = 20;
  const pts = data.map((v, i) => `${(i/(data.length-1))*w},${h - ((v-min)/(max-min||1))*h}`).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline points={pts} fill="none" stroke="#CCFF00" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  );
}

export function PlayerTable({ players: propPlayers }: Props = {}) {
  const rows = propPlayers ?? players;
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-700">
        <p className="font-mono text-xs text-slate-400 uppercase tracking-wide">Joueurs</p>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700">
            {["Joueur","Pos","PTS","REB","AST","+/-","Tendance"].map(h => (
              <th key={h} className="px-4 py-3 text-left font-mono text-xs text-slate-400 font-normal">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p, i) => (
            <tr key={p.id} className={`border-b border-slate-700 hover:bg-ink/50 transition-colors ${i === rows.length-1 ? "border-b-0":""}`}>
              <td className="px-4 py-3 font-geist text-sm text-bone">{p.name}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-400">{p.pos}</td>
              <td className="px-4 py-3 font-mono text-sm text-bone">{p.pts}</td>
              <td className="px-4 py-3 font-mono text-sm text-bone">{p.reb}</td>
              <td className="px-4 py-3 font-mono text-sm text-bone">{p.ast}</td>
              <td className={`px-4 py-3 font-mono text-sm ${p.pm.startsWith("+") ? "text-signal" : "text-court"}`}>{p.pm}</td>
              <td className="px-4 py-3"><Sparkline data={p.trend}/></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
