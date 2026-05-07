"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Eye,
  Activity,
  Target,
  FileText,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { api } from "@/lib/api";
import { useJobPoller } from "@/hooks/useJobPoller";

// ─── Types ────────────────────────────────────────────────────────────────────

type PageState = "idle" | "selected" | "uploading" | "analyzing" | "done" | "error";

// ─── Constants ────────────────────────────────────────────────────────────────

const ACCEPTED = [".mp4", ".mkv", ".avi"];
const MAX_SIZE_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB
const MAX_SIZE_LABEL = "2 Go";

const ANALYSIS_STEPS = [
  { label: "Détection des joueurs", icon: Eye, threshold: 0 },
  { label: "Tracking des trajectoires", icon: Activity, threshold: 30 },
  { label: "Analyse des tirs", icon: Target, threshold: 60 },
  { label: "Génération du rapport", icon: FileText, threshold: 85 },
];

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} Go`;
  if (bytes >= 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  return `${(bytes / 1024).toFixed(0)} Ko`;
}

function activeStepIndex(progress: number): number {
  let active = 0;
  for (let i = ANALYSIS_STEPS.length - 1; i >= 0; i--) {
    if (progress >= ANALYSIS_STEPS[i].threshold) {
      active = i;
      break;
    }
  }
  return active;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
      <motion.div
        className="h-full bg-court rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      />
    </div>
  );
}

function AnalysisStep({
  label,
  icon: Icon,
  state,
}: {
  label: string;
  icon: typeof Eye;
  state: "pending" | "active" | "done";
}) {
  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
        state === "active"
          ? "bg-slate-900 border border-court/40"
          : state === "done"
          ? "bg-slate-900/50"
          : "opacity-40"
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          state === "done"
            ? "bg-signal/20"
            : state === "active"
            ? "bg-court/20"
            : "bg-slate-700"
        }`}
      >
        {state === "done" ? (
          <CheckCircle size={14} className="text-signal" />
        ) : (
          <Icon
            size={14}
            className={state === "active" ? "text-court" : "text-slate-400"}
          />
        )}
      </div>
      <span
        className={`font-geist text-sm ${
          state === "pending" ? "text-slate-400" : "text-bone"
        }`}
      >
        {label}
      </span>
      {state === "active" && (
        <motion.div
          className="ml-auto w-1.5 h-1.5 rounded-full bg-court"
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        />
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [pageState, setPageState] = useState<PageState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  // Polling only active when we have a jobId and are analyzing
  const activeJobId = pageState === "analyzing" ? jobId : null;
  const { job, progress } = useJobPoller(activeJobId);

  // React to job updates
  useEffect(() => {
    if (!job) return;
    if (job.status === "done") setPageState("done");
    if (job.status === "error") {
      setErrorMessage(job.error ?? "Erreur lors de l'analyse.");
      setPageState("error");
    }
  }, [job]);

  // ── File validation ──────────────────────────────────────────────────────

  function validateFile(f: File): string | null {
    const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["mp4", "mkv", "avi"].includes(ext))
      return `Format non supporté (.${ext}). Utilisez MP4, MKV ou AVI.`;
    if (f.size > MAX_SIZE_BYTES)
      return `Fichier trop volumineux (${formatBytes(f.size)}). Maximum ${MAX_SIZE_LABEL}.`;
    return null;
  }

  function handleFile(f: File) {
    const err = validateFile(f);
    if (err) {
      setErrorMessage(err);
      setPageState("error");
      return;
    }
    setFile(f);
    setPageState("selected");
    setErrorMessage("");
  }

  // ── Drag events ──────────────────────────────────────────────────────────

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current += 1;
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current === 0) setIsDragging(false);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Upload + submit ───────────────────────────────────────────────────────

  async function handleSubmit() {
    if (!file) return;
    setPageState("uploading");
    setUploadPct(0);

    const XHR = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    const uploadResult = await new Promise<{ job_id: string } | { error: string }>((resolve) => {
      XHR.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) setUploadPct(Math.round((e.loaded / e.total) * 100));
      });

      XHR.addEventListener("load", () => {
        setUploadPct(100);
        if (XHR.status >= 200 && XHR.status < 300) {
          try {
            const data = JSON.parse(XHR.responseText) as { job_id: string };
            resolve(data);
          } catch {
            resolve({ error: "Réponse invalide du serveur." });
          }
        } else {
          try {
            const body = JSON.parse(XHR.responseText) as { detail?: string };
            resolve({ error: body.detail ?? `HTTP ${XHR.status}` });
          } catch {
            resolve({ error: `HTTP ${XHR.status}` });
          }
        }
      });

      XHR.addEventListener("error", () => resolve({ error: "Échec de la connexion." }));
      XHR.open("POST", `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/analyze`);
      XHR.send(form);
    });

    if ("error" in uploadResult) {
      setErrorMessage(uploadResult.error);
      setPageState("error");
      return;
    }

    setJobId(uploadResult.job_id);
    setPageState("analyzing");
  }

  function handleReset() {
    setFile(null);
    setJobId(null);
    setUploadPct(0);
    setErrorMessage("");
    setPageState("idle");
    dragCounterRef.current = 0;
  }

  const currentStep = activeStepIndex(progress);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-ink text-bone flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Logo className="h-6 w-auto text-bone" />
          <a
            href="/"
            className="flex items-center gap-1.5 font-geist text-xs text-slate-400 hover:text-bone transition-colors"
          >
            <ArrowLeft size={12} />
            Retour à l&apos;accueil
          </a>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 flex flex-col gap-8">
        <div>
          <p className="font-mono text-xs text-court uppercase tracking-widest mb-2">
            Analyse de match
          </p>
          <h1 className="font-fraunces text-3xl text-bone">
            Déposez votre vidéo
          </h1>
          <p className="font-geist text-sm text-slate-400 mt-2">
            Notre pipeline CV analyse vos matchs en moins de 2 minutes.
          </p>
        </div>

        <AnimatePresence mode="wait">

          {/* ── IDLE / SELECTED ──────────────────────────────────────────── */}
          {(pageState === "idle" || pageState === "selected") && (
            <motion.div
              key="drop"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col gap-6"
            >
              {/* Drop zone */}
              <div
                onDragEnter={onDragEnter}
                onDragLeave={onDragLeave}
                onDragOver={onDragOver}
                onDrop={onDrop}
                onClick={() => pageState === "idle" && inputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center gap-4 transition-all cursor-pointer select-none
                  ${isDragging
                    ? "border-court bg-court/5"
                    : pageState === "selected"
                    ? "border-signal/50 bg-signal/5 cursor-default"
                    : "border-slate-700 hover:border-court/60 hover:bg-slate-900/40"
                  }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".mp4,.mkv,.avi"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />

                {pageState === "selected" && file ? (
                  <>
                    <div className="w-14 h-14 rounded-full bg-signal/20 flex items-center justify-center">
                      <CheckCircle size={24} className="text-signal" />
                    </div>
                    <div className="text-center">
                      <p className="font-geist text-sm text-bone font-medium truncate max-w-xs">
                        {file.name}
                      </p>
                      <p className="font-mono text-xs text-slate-400 mt-1">
                        {formatBytes(file.size)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReset();
                      }}
                      className="font-geist text-xs text-slate-400 hover:text-bone underline transition-colors"
                    >
                      Changer de fichier
                    </button>
                  </>
                ) : (
                  <>
                    <div
                      className={`w-14 h-14 rounded-full border-2 flex items-center justify-center transition-colors ${
                        isDragging ? "border-court bg-court/10" : "border-slate-700"
                      }`}
                    >
                      <Upload
                        size={20}
                        className={isDragging ? "text-court" : "text-slate-400"}
                      />
                    </div>
                    <div className="text-center">
                      <p className="font-geist text-sm text-bone">
                        {isDragging
                          ? "Relâchez pour déposer"
                          : "Déposez votre fichier ici ou cliquez pour sélectionner"}
                      </p>
                      <p className="font-mono text-xs text-slate-400 mt-1">
                        MP4, MKV, AVI · max {MAX_SIZE_LABEL}
                      </p>
                    </div>
                  </>
                )}
              </div>

              {/* Submit button */}
              <AnimatePresence>
                {pageState === "selected" && (
                  <motion.button
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    onClick={() => void handleSubmit()}
                    className="w-full py-3.5 bg-court text-ink font-geist font-semibold text-sm rounded-xl hover:bg-court/90 transition-colors"
                  >
                    Analyser avec Songa
                  </motion.button>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ── UPLOADING ────────────────────────────────────────────────── */}
          {pageState === "uploading" && (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-slate-900 border border-slate-700 rounded-2xl p-8 flex flex-col gap-5"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-court/20 flex items-center justify-center">
                  <Upload size={16} className="text-court" />
                </div>
                <div>
                  <p className="font-geist text-sm text-bone">
                    Upload en cours...
                  </p>
                  <p className="font-mono text-xs text-slate-400">
                    {file?.name}
                  </p>
                </div>
                <span className="ml-auto font-mono text-sm text-court">
                  {uploadPct}%
                </span>
              </div>
              <ProgressBar pct={uploadPct} />
            </motion.div>
          )}

          {/* ── ANALYZING ────────────────────────────────────────────────── */}
          {pageState === "analyzing" && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-slate-900 border border-slate-700 rounded-2xl p-8 flex flex-col gap-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-geist text-sm text-bone">
                    Analyse en cours...
                  </p>
                  <p className="font-mono text-xs text-slate-400 mt-0.5">
                    {file?.name}
                  </p>
                </div>
                <span className="font-mono text-sm text-court">{progress}%</span>
              </div>

              <ProgressBar pct={progress} />

              <div className="flex flex-col gap-2">
                {ANALYSIS_STEPS.map((step, idx) => {
                  const state =
                    idx < currentStep
                      ? "done"
                      : idx === currentStep
                      ? "active"
                      : "pending";
                  return (
                    <AnalysisStep
                      key={step.label}
                      label={step.label}
                      icon={step.icon}
                      state={state}
                    />
                  );
                })}
              </div>

              {progress > 0 && progress < 100 && (
                <p className="font-mono text-xs text-slate-400 text-center">
                  Temps restant estimé :{" "}
                  {Math.max(1, Math.round((100 - progress) / 10))} min
                </p>
              )}
            </motion.div>
          )}

          {/* ── DONE ─────────────────────────────────────────────────────── */}
          {pageState === "done" && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-slate-900 border border-signal/30 rounded-2xl p-10 flex flex-col items-center gap-6"
            >
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 16, delay: 0.1 }}
                className="w-16 h-16 rounded-full bg-signal/20 flex items-center justify-center"
              >
                <CheckCircle size={28} className="text-signal" />
              </motion.div>
              <div className="text-center">
                <p className="font-fraunces text-xl text-bone">Analyse terminée</p>
                <p className="font-geist text-sm text-slate-400 mt-1">
                  Votre rapport est prêt.
                </p>
              </div>
              <a
                href={`/results/${jobId}`}
                className="w-full max-w-xs text-center py-3.5 bg-court text-ink font-geist font-semibold text-sm rounded-xl hover:bg-court/90 transition-colors"
              >
                Voir les résultats
              </a>
            </motion.div>
          )}

          {/* ── ERROR ────────────────────────────────────────────────────── */}
          {pageState === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-slate-900 border border-red-900/40 rounded-2xl p-8 flex flex-col items-center gap-5"
            >
              <div className="w-12 h-12 rounded-full bg-red-900/20 flex items-center justify-center">
                <AlertCircle size={20} className="text-red-400" />
              </div>
              <div className="text-center">
                <p className="font-geist text-sm text-bone">
                  Une erreur est survenue
                </p>
                {errorMessage && (
                  <p className="font-mono text-xs text-slate-400 mt-2 max-w-sm">
                    {errorMessage}
                  </p>
                )}
              </div>
              <button
                onClick={handleReset}
                className="py-2.5 px-6 border border-slate-700 hover:border-slate-400 text-slate-400 hover:text-bone font-geist text-sm rounded-xl transition-all"
              >
                Réessayer
              </button>
            </motion.div>
          )}

        </AnimatePresence>

        {/* ── Specs ───────────────────────────────────────────────────────── */}
        <div className="border-t border-slate-700 pt-8">
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest mb-4">
            Formats supportés
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label: "Formats vidéo", value: "MP4, MKV, AVI" },
              { label: "Résolution max", value: "4K / 1080p" },
              { label: "Fréquence min.", value: "30 fps" },
              { label: "Taille max.", value: MAX_SIZE_LABEL },
              { label: "Durée max.", value: "3h" },
              { label: "Traitement", value: "< 2 min" },
            ].map((spec) => (
              <div
                key={spec.label}
                className="bg-slate-900 border border-slate-700 rounded-lg p-3"
              >
                <p className="font-mono text-xs text-slate-400">{spec.label}</p>
                <p className="font-geist text-sm text-bone mt-0.5">{spec.value}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
