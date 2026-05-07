"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";
import { Eye, BarChart2, Users, FileText } from "lucide-react";

const icons = [Eye, BarChart2, Users, FileText];

export function Features() {
  const { t } = useLang();
  return (
    <section id="features" className="py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-16">
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{t.features.label}</p>
          <h2 className="font-fraunces text-4xl lg:text-5xl text-bone whitespace-pre-line leading-tight">{t.features.headline}</h2>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {t.features.items.map((f, i) => {
            const Icon = icons[i];
            return (
              <motion.div
                key={i}
                className="bg-slate-900 border border-slate-700 rounded-xl p-8 hover:border-slate-400 transition-all duration-200 hover:-translate-y-1 group"
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true, amount: 0.3 }}
              >
                <div className="w-10 h-10 rounded-lg border border-slate-700 group-hover:border-court flex items-center justify-center mb-6 transition-colors">
                  <Icon size={18} className="text-slate-400 group-hover:text-court transition-colors" />
                </div>
                <h3 className="font-fraunces text-xl text-bone mb-3">{f.title}</h3>
                <p className="font-geist text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
