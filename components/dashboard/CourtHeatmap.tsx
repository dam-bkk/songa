"use client";
import { shotZones } from "@/lib/mockData";

export interface ShotZone {
  zone: string;
  made: number;
  attempted: number;
  x: number;
  y: number;
}

interface Props {
  data?: ShotZone[];
}

function zoneColor(made: number, attempted: number) {
  const pct = made / attempted;
  if (pct >= 0.55) return "#0055FF";
  if (pct >= 0.40) return "#CCFF00";
  return "#9A9389";
}

export function CourtHeatmap({ data }: Props = {}) {
  const zones = data ?? shotZones;
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
      <p className="font-mono text-xs text-slate-400 uppercase tracking-wide mb-4">Shot Chart</p>
      <div className="relative">
        <svg viewBox="0 0 500 375" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
          <rect x="10" y="10" width="480" height="355" rx="4" stroke="#3A3631" strokeWidth="1.5" fill="#1A1815"/>
          <rect x="10" y="130" width="120" height="115" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <circle cx="60" cy="187" r="12" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <path d="M 10 80 Q 200 187 10 294" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <line x1="250" y1="10" x2="250" y2="365" stroke="#3A3631" strokeWidth="1" strokeDasharray="4 4"/>
          <circle cx="250" cy="187" r="40" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <rect x="370" y="130" width="120" height="115" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <circle cx="440" cy="187" r="12" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          <path d="M 490 80 Q 300 187 490 294" stroke="#3A3631" strokeWidth="1.5" fill="none"/>
          {zones.map((z, i) => (
            <g key={i}>
              <circle cx={z.x} cy={z.y} r="22" fill={zoneColor(z.made, z.attempted)} fillOpacity="0.25" stroke={zoneColor(z.made, z.attempted)} strokeWidth="1"/>
              <text x={z.x} y={z.y - 6} textAnchor="middle" fontSize="10" fill={zoneColor(z.made, z.attempted)} fontFamily="var(--font-jetbrains-var)">{z.made}/{z.attempted}</text>
              <text x={z.x} y={z.y + 8} textAnchor="middle" fontSize="9" fill={zoneColor(z.made, z.attempted)} fontFamily="var(--font-jetbrains-var)">{Math.round(z.made/z.attempted*100)}%</text>
            </g>
          ))}
        </svg>
      </div>
      <div className="flex gap-4 mt-4">
        {[{color:"#0055FF",label:"≥55%"},{color:"#CCFF00",label:"40–54%"},{color:"#9A9389",label:"<40%"}].map(l => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{background:l.color}}/>
            <span className="font-mono text-xs text-slate-400">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
