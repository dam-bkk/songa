"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";
import { ArrowRight } from "lucide-react";

export function Audience() {
  const { t } = useLang();
  return (
    <section id="audience" className="py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-16">
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{t.audience.label}</p>
          <h2 className="font-fraunces text-4xl lg:text-5xl text-bone">{t.audience.headline}</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {([
            { key: "coach", href: "/demo/coach", data: t.audience.coach },
            { key: "academy", href: "/demo/academy", data: t.audience.academy },
          ] as const).map(({ href, data }, i) => (
            <motion.a
              key={i} href={href}
              className="group block bg-slate-900 border border-slate-700 hover:border-court rounded-xl p-10 transition-all duration-200 hover:-translate-y-1"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              viewport={{ once: true, amount: 0.3 }}
            >
              <h3 className="font-fraunces text-3xl text-bone mb-4">{data.title}</h3>
              <p className="font-geist text-sm text-slate-400 leading-relaxed mb-8">{data.desc}</p>
              <span className="flex items-center gap-2 text-sm font-geist text-court group-hover:gap-3 transition-all">
                {data.cta} <ArrowRight size={14} />
              </span>
            </motion.a>
          ))}
        </div>
      </div>
    </section>
  );
}
