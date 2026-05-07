"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";

export function HowItWorks() {
  const { t } = useLang();
  return (
    <section id="how" className="py-24 px-6 bg-slate-900">
      <div className="max-w-7xl mx-auto">
        <div className="mb-16">
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{t.how.label}</p>
          <h2 className="font-fraunces text-4xl lg:text-5xl text-bone">{t.how.headline}</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-px bg-slate-700 rounded-xl overflow-hidden">
          {t.how.steps.map((s, i) => (
            <motion.div
              key={i}
              className="bg-slate-900 p-10"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15, duration: 0.5 }}
              viewport={{ once: true, amount: 0.3 }}
            >
              <span className="font-mono text-5xl font-medium text-slate-700 block mb-8">{s.num}</span>
              <h3 className="font-fraunces text-2xl text-bone mb-4">{s.title}</h3>
              <p className="font-geist text-sm text-slate-400 leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
