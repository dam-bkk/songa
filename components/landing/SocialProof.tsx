"use client";
import { motion } from "framer-motion";
import { useLang } from "@/lib/i18n";

function AvatarPlaceholder({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("");
  return (
    <div className="w-10 h-10 rounded-full bg-slate-700 border border-slate-700 flex items-center justify-center flex-shrink-0">
      <span className="font-mono text-xs text-slate-400 select-none">{initials}</span>
    </div>
  );
}

export function SocialProof() {
  const { t } = useLang();
  const ts = t.social_proof;

  return (
    <section id="social-proof" className="py-24 px-6 border-t border-slate-700">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-16">
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">{ts.label}</p>
          <h2 className="font-fraunces text-4xl lg:text-5xl text-bone leading-tight">{ts.headline}</h2>
        </div>

        {/* Quotes grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-20">
          {ts.quotes.map((quote, i) => (
            <motion.div
              key={i}
              className="bg-slate-900 border border-slate-700 rounded-xl p-8 flex flex-col gap-6"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.12, duration: 0.5 }}
              viewport={{ once: true, amount: 0.3 }}
            >
              {/* Quote mark */}
              <div className="w-6 h-4 flex-shrink-0">
                <svg viewBox="0 0 24 16" fill="none" className="w-full h-full">
                  <path
                    d="M0 16V9.6C0 4.267 2.667 1.067 8 0l1.6 2.4C7.2 3.2 6 5.067 6 8H10V16H0ZM14 16V9.6C14 4.267 16.667 1.067 22 0l1.6 2.4C21.2 3.2 20 5.067 20 8H24V16H14Z"
                    fill="currentColor"
                    className="text-slate-700"
                  />
                </svg>
              </div>

              <p className="font-geist text-sm text-slate-400 leading-relaxed flex-1">
                {quote.text}
              </p>

              <div className="flex items-center gap-3">
                <AvatarPlaceholder name={quote.author} />
                <div>
                  <p className="font-geist text-sm text-bone font-medium">{quote.author}</p>
                  <p className="font-mono text-xs text-slate-400">{quote.role} · {quote.club}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Orgs strip */}
        <motion.div
          className="flex flex-wrap items-center justify-center gap-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          viewport={{ once: true }}
        >
          {ts.orgs.map((org, i) => (
            <span
              key={i}
              className="font-mono text-xs text-slate-400/50 uppercase tracking-widest select-none"
            >
              {org}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
