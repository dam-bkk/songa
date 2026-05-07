"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check } from "lucide-react";
import { useLang } from "@/lib/i18n";
import { useDemoModal } from "@/lib/demoModal";

export function Pricing() {
  const { t } = useLang();
  const { open } = useDemoModal();
  const tp = t.pricing;
  const [yearly, setYearly] = useState(false);

  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-14 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-8">
          <div>
            <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{tp.label}</p>
            <h2 className="font-fraunces text-4xl lg:text-5xl text-bone leading-tight">{tp.headline}</h2>
            <p className="font-geist text-sm text-slate-400 mt-4">{tp.sub}</p>
          </div>

          {/* Toggle */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className={`font-geist text-sm transition-colors ${!yearly ? "text-bone" : "text-slate-400"}`}>
              {tp.monthly}
            </span>
            <button
              onClick={() => setYearly((v) => !v)}
              className="relative w-12 h-6 rounded-full bg-slate-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-court"
              aria-checked={yearly}
              role="switch"
              aria-label="Facturation annuelle"
            >
              <motion.div
                className="absolute top-1 left-1 w-4 h-4 rounded-full bg-bone"
                animate={{ x: yearly ? 24 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            </button>
            <span className={`font-geist text-sm transition-colors ${yearly ? "text-bone" : "text-slate-400"}`}>
              {tp.yearly}
            </span>
            <AnimatePresence>
              {yearly && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="font-mono text-xs text-signal border border-signal/40 bg-signal/10 px-2 py-0.5 rounded-full"
                >
                  {tp.save}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Cards */}
        <div className="grid lg:grid-cols-3 gap-4">
          {tp.plans.map((plan, i) => {
            const price = yearly ? plan.price_yr : plan.price_mo;
            const suffix = yearly ? tp.yr : tp.mo;
            const isFederation = i === 2;
            const isPopular = plan.popular;

            return (
              <motion.div
                key={plan.name}
                className={`relative rounded-2xl p-8 flex flex-col transition-all duration-200 ${
                  isPopular
                    ? "bg-slate-900 border-2 border-court shadow-[0_0_40px_-8px_rgba(232,116,60,0.25)]"
                    : "bg-slate-900 border border-slate-700 hover:border-slate-400"
                }`}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true, amount: 0.2 }}
              >
                {/* Popular badge */}
                {isPopular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <span className="font-mono text-xs text-ink bg-court px-3 py-1 rounded-full whitespace-nowrap">
                      {tp.popular}
                    </span>
                  </div>
                )}

                {/* Plan name & desc */}
                <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-2">{plan.name}</p>
                <p className="font-geist text-sm text-slate-400 mb-6 leading-relaxed">{plan.desc}</p>

                {/* Price */}
                <div className="mb-8">
                  {isFederation ? (
                    <div className="flex items-baseline gap-1">
                      <AnimatePresence mode="wait">
                        <motion.span
                          key={`${plan.name}-${yearly}`}
                          initial={{ opacity: 0, y: -8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 8 }}
                          transition={{ duration: 0.2 }}
                          className="font-fraunces text-4xl text-bone"
                        >
                          {price}€
                        </motion.span>
                      </AnimatePresence>
                      <span className="font-geist text-sm text-slate-400">{suffix}</span>
                      {yearly && (
                        <span className="ml-2 font-mono text-xs text-signal border border-signal/40 bg-signal/10 px-1.5 py-0.5 rounded-full">
                          {tp.save}
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-baseline gap-1">
                      <AnimatePresence mode="wait">
                        <motion.span
                          key={`${plan.name}-${yearly}`}
                          initial={{ opacity: 0, y: -8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 8 }}
                          transition={{ duration: 0.2 }}
                          className="font-fraunces text-4xl text-bone"
                        >
                          {price}€
                        </motion.span>
                      </AnimatePresence>
                      <span className="font-geist text-sm text-slate-400">{suffix}</span>
                      {yearly && (
                        <span className="ml-2 font-mono text-xs text-signal border border-signal/40 bg-signal/10 px-1.5 py-0.5 rounded-full">
                          {tp.save}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feature, fi) => (
                    <li key={fi} className="flex items-start gap-3">
                      <Check size={14} className="text-signal flex-shrink-0 mt-0.5" />
                      <span className="font-geist text-sm text-slate-400 leading-relaxed">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                {isFederation ? (
                  <button
                    onClick={open}
                    className="w-full font-geist text-sm font-medium py-3 px-6 rounded-lg border border-slate-700 text-bone hover:border-slate-400 hover:bg-slate-700/50 transition-all"
                  >
                    {tp.cta_demo}
                  </button>
                ) : (
                  <button
                    className={`w-full font-geist text-sm font-medium py-3 px-6 rounded-lg transition-all ${
                      isPopular
                        ? "bg-court text-ink hover:bg-court/90"
                        : "border border-slate-700 text-bone hover:border-slate-400 hover:bg-slate-700/50"
                    }`}
                  >
                    {tp.cta}
                  </button>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
