"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";

export function StatsBar() {
  const { t } = useLang();
  return (
    <section className="border-y border-slate-700 bg-ink py-8">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4">
        {t.stats.map((s, i) => (
          <motion.div
            key={i}
            className={`flex flex-col items-center py-6 ${i < t.stats.length - 1 ? "md:border-r border-slate-700" : ""}`}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.5 }}
            viewport={{ once: true, amount: 0.5 }}
          >
            <span className="font-fraunces text-4xl font-light text-bone mb-2">{s.value}</span>
            <span className="font-mono text-xs text-slate-400 tracking-wide text-center">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
