"use client";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, Loader2, Send } from "lucide-react";
import { useDemoModal } from "@/lib/demoModal";
import { useLang } from "@/lib/i18n";

type FormState = "idle" | "loading" | "success";

const inputClass =
  "w-full bg-ink border border-slate-700 rounded-lg px-4 py-3 font-geist text-sm text-bone placeholder:text-slate-400 focus:outline-none focus:border-court transition-colors";

const labelClass = "block font-mono text-xs text-slate-400 uppercase tracking-widest mb-2";

export function DemoModal() {
  const { isOpen, close } = useDemoModal();
  const { t } = useLang();
  const td = t.demo;

  const [formState, setFormState] = useState<FormState>("idle");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [fields, setFields] = useState({
    name: "",
    email: "",
    club: "",
    role: "",
    message: "",
  });

  const firstInputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Focus trap
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => firstInputRef.current?.focus(), 50);
    } else {
      setFormState("idle");
      setErrors({});
      setFields({ name: "", email: "", club: "", role: "", message: "" });
    }
  }, [isOpen]);

  // ESC to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, close]);

  // Auto-close after success
  useEffect(() => {
    if (formState === "success") {
      const t = setTimeout(() => close(), 3000);
      return () => clearTimeout(t);
    }
  }, [formState, close]);

  function set(key: keyof typeof fields, val: string) {
    setFields((f) => ({ ...f, [key]: val }));
    if (errors[key]) setErrors((e) => { const n = { ...e }; delete n[key]; return n; });
  }

  function validate() {
    const e: Record<string, string> = {};
    if (!fields.name.trim()) e.name = "Requis";
    if (!fields.email.trim()) e.email = "Requis";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) e.email = "Email invalide";
    if (!fields.club.trim()) e.club = "Requis";
    if (!fields.role) e.role = "Requis";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setFormState("loading");
    try {
      const res = await fetch("/api/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields),
      });
      if (res.ok) {
        setFormState("success");
      } else {
        setFormState("idle");
      }
    } catch {
      setFormState("idle");
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => { if (e.target === overlayRef.current) close(); }}
          aria-modal="true"
          role="dialog"
          aria-label={td.title}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-ink/80 backdrop-blur-sm" />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-3xl bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl"
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.25, ease: [0.32, 0.72, 0, 1] }}
          >
            {/* Close button */}
            <button
              onClick={close}
              className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-bone hover:bg-slate-700 transition-colors"
              aria-label="Fermer"
            >
              <X size={16} />
            </button>

            <div className="grid md:grid-cols-[1fr_1.5fr]">
              {/* Left — pitch */}
              <div className="bg-court/10 border-r border-slate-700 p-8 flex flex-col justify-between hidden md:flex">
                <div>
                  <div className="w-10 h-10 rounded-lg bg-court/20 border border-court/40 flex items-center justify-center mb-6">
                    <Send size={18} className="text-court" />
                  </div>
                  <h2 className="font-fraunces text-2xl text-bone mb-3 leading-snug">{td.title}</h2>
                  <p className="font-geist text-sm text-slate-400 leading-relaxed">{td.subtitle}</p>
                </div>
                <div className="mt-8 space-y-3">
                  {[
                    "Démo personnalisée sur vos matchs",
                    "Réponse sous 24 heures",
                    "Sans engagement",
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-signal flex-shrink-0" />
                      <span className="font-geist text-xs text-slate-400">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right — form */}
              <div className="p-8">
                {/* Success state */}
                {formState === "success" ? (
                  <motion.div
                    className="h-full flex flex-col items-center justify-center text-center py-12"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.1 }}
                    >
                      <CheckCircle size={56} className="text-signal mx-auto mb-6" />
                    </motion.div>
                    <p className="font-fraunces text-xl text-bone mb-2">{td.success}</p>
                  </motion.div>
                ) : (
                  <form onSubmit={handleSubmit} noValidate>
                    <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-6 md:hidden">{td.title}</p>

                    <div className="grid sm:grid-cols-2 gap-4 mb-4">
                      {/* Name */}
                      <div>
                        <label className={labelClass}>{td.name}</label>
                        <input
                          ref={firstInputRef}
                          type="text"
                          value={fields.name}
                          onChange={(e) => set("name", e.target.value)}
                          placeholder="Kouadio Jean-Marie"
                          className={`${inputClass} ${errors.name ? "border-red-500" : ""}`}
                          disabled={formState === "loading"}
                        />
                        {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name}</p>}
                      </div>

                      {/* Email */}
                      <div>
                        <label className={labelClass}>{td.email}</label>
                        <input
                          type="email"
                          value={fields.email}
                          onChange={(e) => set("email", e.target.value)}
                          placeholder="jean-marie@club.ci"
                          className={`${inputClass} ${errors.email ? "border-red-500" : ""}`}
                          disabled={formState === "loading"}
                        />
                        {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email}</p>}
                      </div>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-4 mb-4">
                      {/* Club */}
                      <div>
                        <label className={labelClass}>{td.club}</label>
                        <input
                          type="text"
                          value={fields.club}
                          onChange={(e) => set("club", e.target.value)}
                          placeholder="ABC Fighters"
                          className={`${inputClass} ${errors.club ? "border-red-500" : ""}`}
                          disabled={formState === "loading"}
                        />
                        {errors.club && <p className="mt-1 text-xs text-red-400">{errors.club}</p>}
                      </div>

                      {/* Role */}
                      <div>
                        <label className={labelClass}>{td.role}</label>
                        <select
                          value={fields.role}
                          onChange={(e) => set("role", e.target.value)}
                          className={`${inputClass} ${errors.role ? "border-red-500" : ""} appearance-none cursor-pointer`}
                          disabled={formState === "loading"}
                        >
                          <option value="" disabled>—</option>
                          {td.roles.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                        {errors.role && <p className="mt-1 text-xs text-red-400">{errors.role}</p>}
                      </div>
                    </div>

                    {/* Message */}
                    <div className="mb-6">
                      <label className={labelClass}>{td.message}</label>
                      <textarea
                        value={fields.message}
                        onChange={(e) => set("message", e.target.value)}
                        rows={3}
                        placeholder="Décrivez votre contexte, vos besoins..."
                        className={`${inputClass} resize-none`}
                        disabled={formState === "loading"}
                      />
                    </div>

                    {/* Submit */}
                    <button
                      type="submit"
                      disabled={formState === "loading"}
                      className="w-full flex items-center justify-center gap-2 bg-court text-ink font-medium py-3 px-6 rounded-lg hover:bg-court/90 transition-colors font-geist text-sm disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {formState === "loading" ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : null}
                      {td.submit}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
