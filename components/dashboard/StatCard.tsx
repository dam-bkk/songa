interface Props { label: string; value: string; sub?: string }
export function StatCard({ label, value, sub }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
      <p className="font-mono text-xs text-slate-400 uppercase tracking-wide mb-3">{label}</p>
      <p className="font-fraunces text-4xl text-bone">{value}</p>
      {sub && <p className="font-geist text-xs text-slate-400 mt-2">{sub}</p>}
    </div>
  );
}
