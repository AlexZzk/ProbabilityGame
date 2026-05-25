export interface Draw {
  id: number;
  period: string;
  red_balls: number[];
  blue_ball: number;
  draw_date: string | null;
  created_at: string;
}

export interface PredictionItem {
  id: number;
  red_balls: number[];
  blue_ball: number;
  red_hits: number | null;
  blue_hit: boolean | null;
  prize_level: number | null;
}

export interface Prediction {
  id: number;
  strategy: string;
  count: number;
  target_period: string | null;
  notes: string | null;
  created_at: string;
  items: PredictionItem[];
}

export interface FrequencyStats {
  red: Record<string, number>;
  blue: Record<string, number>;
  total_draws: number;
}

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  listDraws: () => http<Draw[]>("/api/draws?limit=500"),
  countDraws: () => http<{ total: number }>("/api/draws/count"),
  createDraw: (payload: Omit<Draw, "id" | "created_at">) =>
    http<Draw>("/api/draws", { method: "POST", body: JSON.stringify(payload) }),
  uploadCsv: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/draws/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ inserted_or_updated: number }>;
  },
  frequency: (window?: number) =>
    http<FrequencyStats>(`/api/draws/stats/frequency${window ? `?window=${window}` : ""}`),

  predict: (body: {
    count: number;
    strategy: string;
    target_period?: string;
    notes?: string;
    window?: number;
  }) =>
    http<Prediction>("/api/predictions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listPredictions: () => http<Prediction[]>("/api/predictions?limit=100"),

  // ML model
  modelState: () => http<ModelState>("/api/model"),
  modelTrain: (fullRetrain = false) =>
    http<{ trained: number; calibrated: number; version: number }>(
      `/api/model/train?full_retrain=${fullRetrain}`,
      { method: "POST" },
    ),
  modelReset: () => http<ModelState>("/api/model/reset", { method: "POST" }),
  modelEvents: () => http<ModelEvent[]>("/api/model/events?limit=2000"),
};

export interface ModelState {
  name: string;
  version: number;
  temperature: number;
  learning_rate: number;
  decay: number;
  prior_strength: number;
  last_trained_draw_id: number | null;
  red_alpha: number[];
  blue_alpha: number[];
  red_probs: number[];
  blue_probs: number[];
  updated_at: string | null;
}

export interface ModelEvent {
  id: number;
  event_type: string;
  version: number;
  draw_id: number | null;
  nll: number | null;
  nll_red: number | null;
  nll_blue: number | null;
  temperature_before: number | null;
  temperature_after: number | null;
  kl_red_vs_model: number | null;
  kl_red_vs_uniform: number | null;
  kl_blue_vs_model: number | null;
  kl_blue_vs_uniform: number | null;
  decision: string | null;
  created_at: string;
}
