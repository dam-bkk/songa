const BASE_URL =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export interface AnalysisJob {
  job_id: string;
  status: "queued" | "processing" | "done" | "error";
  video_name: string;
  progress: number;
  result_path?: string;
  error?: string;
}

export interface MatchStats {
  meta: {
    game: string;
    date: string;
    duration_s: number;
    fps: number;
    frames_analyzed: number;
  };
  team_stats: {
    possession_pct: number;
    avg_spacing_m: number;
    paint_touches: number;
    transition_speed_ms: number;
  };
  player_stats: Record<
    string,
    {
      name: string;
      pos: string;
      total_distance_m: number;
      avg_speed_ms: number;
      max_speed_ms: number;
      time_in_paint_s: number;
      shots_attempted: number;
      shots_made: number;
      shot_pct: number;
    }
  >;
  shot_chart: Record<
    string,
    { made: number; attempted: number; pct: number }
  >;
  key_events: Array<{ time_s: number; type: string; player: string }>;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async submitAnalysis(file: File): Promise<AnalysisJob> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE_URL}/analyze`, { method: "POST", body: form });
    if (!res.ok) {
      let message = `HTTP ${res.status}`;
      try {
        const body = (await res.json()) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // ignore
      }
      throw new ApiError(res.status, message);
    }
    return res.json() as Promise<AnalysisJob>;
  },

  async getJob(jobId: string): Promise<AnalysisJob> {
    return request<AnalysisJob>(`/jobs/${encodeURIComponent(jobId)}`);
  },

  async getResults(jobId: string): Promise<MatchStats> {
    return request<MatchStats>(`/jobs/${encodeURIComponent(jobId)}/results`);
  },

  async getDemoStats(): Promise<MatchStats> {
    return request<MatchStats>("/demo/stats");
  },

  async healthCheck(): Promise<boolean> {
    try {
      await request<unknown>("/health");
      return true;
    } catch {
      return false;
    }
  },
};
