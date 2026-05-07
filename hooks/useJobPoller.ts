import { useState, useEffect, useRef, useCallback, startTransition } from "react";
import { api, type AnalysisJob } from "@/lib/api";

const BACKOFF = [2000, 3000, 5000]; // ms — caps at last value

function getInterval(tickCount: number): number {
  const idx = Math.min(tickCount, BACKOFF.length - 1);
  return BACKOFF[idx];
}

export interface JobPollerResult {
  job: AnalysisJob | null;
  isLoading: boolean;
  isComplete: boolean;
  isError: boolean;
  progress: number;
}

export function useJobPoller(jobId: string | null): JobPollerResult {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [tickCount, setTickCount] = useState(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const clearTimer = useCallback(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const poll = useCallback(
    async (id: string, tick: number) => {
      try {
        const result = await api.getJob(id);
        if (!mountedRef.current) return;
        setJob(result);

        const isTerminal = result.status === "done" || result.status === "error";
        if (!isTerminal) {
          const delay = getInterval(tick);
          timeoutRef.current = setTimeout(() => {
            setTickCount((t) => t + 1);
          }, delay);
        }
      } catch {
        if (!mountedRef.current) return;
        // On network error, keep retrying with capped backoff
        const delay = getInterval(tick);
        timeoutRef.current = setTimeout(() => {
          setTickCount((t) => t + 1);
        }, delay);
      }
    },
    [],
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!jobId) {
      startTransition(() => {
        setJob(null);
        setIsLoading(false);
        setTickCount(0);
      });
      clearTimer();
      return;
    }

    const isTerminal = job?.status === "done" || job?.status === "error";
    if (isTerminal) return;

    startTransition(() => setIsLoading(true));
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void poll(jobId, tickCount).then(() => {
      if (mountedRef.current) startTransition(() => setIsLoading(false));
    });

    return clearTimer;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, tickCount]);

  const isComplete = job?.status === "done";
  const isError = job?.status === "error";

  return {
    job,
    isLoading,
    isComplete: isComplete ?? false,
    isError: isError ?? false,
    progress: job?.progress ?? 0,
  };
}
