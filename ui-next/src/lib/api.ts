const API_BASE =
  typeof window !== "undefined"
    ? "/acorn-api"
    : process.env.API_BACKEND_URL || "http://acorn-api:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// -- Types --

export interface Problem {
  id: string;
  title: string;
  description: string | null;
  status: string;
  solution_url: string | null;
  idempotency_key: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Task {
  id: string;
  problem_id: string;
  title: string;
  description: string | null;
  task_type: string;
  status: string;
  assigned_to: string | null;
  created_at: string;
}

export interface Agent {
  agent_id: string;
  role: string;
  problem_uuid: string | null;
  status: string;
  container_id: string | null;
  last_seen: string | null;
}

export interface Kernel {
  id: string;
  name: string;
  category: string;
  status: string;
  use_count: number;
  description: string;
  created_at: string;
  trigger_keywords?: string[];
  filesystem_path?: string;
  verified_on_problems?: string[];
  source_problem_id?: string;
  content?: string;
}

export interface HealthData {
  status: string;
  acorn_mode: string;
  routing_strategy: string;
  models: Record<string, string>;
  feature_flags: Record<string, boolean>;
  api_key_present: boolean;
  max_agents_per_problem: number;
  max_concurrent_problems: number;
}

export interface TelemetryData {
  total_events: number;
  total_escalations: number;
  escalation_rate_pct: number;
  events_by_type: Record<string, number>;
  active_problems: number;
  recent_events: Record<string, unknown>[];
}

export interface JudgeVerdict {
  id: string;
  task_id: string;
  verdict: string;
  checks: Record<string, unknown>;
  notes: string | null;
  created_at: string;
}

export interface WorkspaceFile {
  name: string;
  size: number;
}

export interface ReasoningStep {
  id: string;
  agent_id: string;
  step_type: string;
  summary: string;
  confidence: number | null;
  sources: unknown[];
  created_at: string;
}

export interface ReasoningTrail {
  problem_id: string;
  steps: ReasoningStep[];
  count: number;
}

export interface HealthMetrics {
  kernel_grove_coverage: { domains_with_3plus_permanent: number };
  judge_pass_rate_7d: number;
  kernel_promotion_rate_7d: number;
  median_time_to_solution_minutes: number | null;
  reasoning_trail_completeness: number;
  ws_streaming_coverage: number;
}

export interface BuilderStatus {
  status: string;
  builder_enabled: boolean;
  cycle_count?: number;
  last_action?: string;
  last_action_result?: string;
  last_action_time?: string;
  thoughts?: string[];
  circuit_breaker: {
    state: string;
    consecutive_failures: number;
  };
  current_sprint: Record<string, unknown> | null;
  last_sprint_result: {
    sprint?: number;
    passed: number;
    failed: number;
    kernels: number;
    committed: boolean;
    breaker?: string;
  } | null;
}

export interface BuilderHistory {
  sprint_count: number;
  total_kernels: number;
  total_skills: number;
  total_commits: number;
  release_count: number;
  stories_since_release: number;
  domain_baselines: Record<string, number>;
  recent_sprints: Array<{
    sprint_number: number;
    started_at: string;
    finished_at?: string;
    problems_submitted: number;
    problems_passed: number;
    kernels_ingested: number;
    skills_ingested: number;
    changes_committed: boolean;
    circuit_breaker_state: string;
    action?: string;
    summary?: string;
    success?: boolean;
    domain_results?: Record<string, unknown>;
  }>;
}

export interface BuilderThoughts {
  thoughts: string[];
  total: number;
}

// -- API functions --

export const api = {
  health: () => apiFetch<HealthData>("/health"),

  problems: {
    list: () => apiFetch<Problem[]>("/api/problems"),
    get: (id: string) => apiFetch<Problem>(`/api/problems/${id}`),
    create: (data: { title: string; description: string }) =>
      apiFetch<Problem>("/api/problems", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    start: (id: string) =>
      apiFetch<{ id: string; status: string; container_name: string; message: string }>(
        `/api/problems/${id}/start`,
        { method: "POST" }
      ),
    delete: (id: string) =>
      apiFetch<void>(`/api/problems/${id}`, { method: "DELETE" }),
    updateStatus: (id: string, status: string) =>
      apiFetch<Problem>(`/api/problems/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    cleanup: () =>
      apiFetch<{ cleaned: number; total_checked: number }>("/api/problems/cleanup", {
        method: "POST",
      }),
    upload: async (id: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/problems/${id}/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json();
    },
    logs: (id: string) =>
      apiFetch<{ container: string; logs: string }>(`/api/problems/${id}/logs`),
    status: (id: string) =>
      apiFetch<{ container: string; container_status: string }>(
        `/api/problems/${id}/status`
      ),
    files: (id: string) =>
      apiFetch<{ files: WorkspaceFile[]; workspace: string }>(
        `/api/problems/${id}/files`
      ),
    fileUrl: (id: string, filename: string) =>
      `${API_BASE}/api/problems/${id}/files/${encodeURIComponent(filename)}`,
    reasoningTrail: (id: string) =>
      apiFetch<ReasoningTrail>(`/api/problems/${id}/reasoning-trail`),
  },

  tasks: {
    list: (problemId: string) =>
      apiFetch<Task[]>(`/api/tasks?problem_id=${problemId}`),
  },

  agents: {
    status: () => apiFetch<Agent[]>("/api/agents/status"),
    models: () => apiFetch<{ models: Record<string, string>; role_routing: Record<string, string> }>("/api/agents/models"),
  },

  kernels: {
    list: (params?: { query?: string; category?: string; status?: string }) => {
      const sp = new URLSearchParams();
      if (params?.query) sp.set("query", params.query);
      if (params?.category && params.category !== "all") sp.set("category", params.category);
      if (params?.status && params.status !== "all") sp.set("status", params.status);
      const qs = sp.toString();
      return apiFetch<Kernel[]>(`/api/kernels${qs ? `?${qs}` : ""}`);
    },
    promote: (id: string) =>
      apiFetch<unknown>(`/api/kernels/${id}/promote`, { method: "POST" }),
  },

  builder: {
    status: () => apiFetch<BuilderStatus>("/api/builder/status"),
    history: () => apiFetch<BuilderHistory>("/api/builder/history"),
    thoughts: () => apiFetch<BuilderThoughts>("/api/builder/thoughts"),
    cortexState: () => apiFetch<BuilderStatus>("/api/builder/cortex-state"),
    startSprint: () =>
      apiFetch<{ status: string }>("/api/builder/start-sprint", { method: "POST" }),
    pause: () =>
      apiFetch<{ status: string }>("/api/builder/pause", { method: "POST" }),
    resume: () =>
      apiFetch<{ status: string }>("/api/builder/resume", { method: "POST" }),
    stop: () =>
      apiFetch<{ status: string; harnesses_stopped?: number }>("/api/builder/stop", { method: "POST" }),
  },

  telemetry: () => apiFetch<TelemetryData>("/api/telemetry"),

  meta: {
    healthMetrics: () => apiFetch<HealthMetrics>("/api/meta/health-metrics"),
  },

  judgeVerdicts: (problemId: string) =>
    apiFetch<JudgeVerdict[]>(`/api/judge_verdicts/${problemId}`),

  rewards: {
    events: (limit = 50) =>
      apiFetch<
        Array<{
          id: string;
          problem_id: string | null;
          agent_id: string;
          role: string;
          signal: string;
          points: number;
          rationale: string | null;
          created_at: string;
        }>
      >(`/api/rewards/events?limit=${limit}`),
    roleScores: () =>
      apiFetch<
        Array<{
          role: string;
          cumulative_points: number;
          rolling_30d_points: number;
          problems_contributed: number;
          last_updated: string;
        }>
      >("/api/rewards/role-scores"),
    roleContext: (role: string) =>
      apiFetch<{
        role: string;
        recent_wins: Array<{
          signal: string;
          points: number;
          rationale: string | null;
          at: string;
        }>;
        recent_misses: Array<{
          signal: string;
          points: number;
          rationale: string | null;
          at: string;
        }>;
        score: {
          cumulative: number;
          rolling_30d: number;
          problems: number;
        };
      }>(`/api/rewards/role-context/${role}`),
  },

  cortex: {
    status: () =>
      apiFetch<{
        running: boolean;
        current_broadcast: {
          module: string;
          salience: number;
          action_type: string;
          payload: Record<string, unknown>;
          all_saliences?: Record<string, number>;
        } | null;
        tick_interval: number;
        broadcast_log_size: number;
      }>("/api/cortex/status"),
    modules: () =>
      apiFetch<Array<{ module: string; salience: number }>>("/api/cortex/modules"),
    broadcastLog: (limit = 50) =>
      apiFetch<
        Array<{
          module: string;
          salience: number;
          action_type: string;
          payload: Record<string, unknown>;
          timestamp: number;
          all_saliences: Record<string, number>;
        }>
      >(`/api/cortex/broadcast-log?limit=${limit}`),
    start: () =>
      apiFetch<{ status: string }>("/api/cortex/start", { method: "POST" }),
    stop: () =>
      apiFetch<{ status: string }>("/api/cortex/stop", { method: "POST" }),
  },

  manifest: {
    status: () =>
      apiFetch<{
        desired: Record<string, unknown>;
        actual: Record<string, unknown>;
      }>("/api/manifest/status"),
    deltas: () =>
      apiFetch<Array<{ type: string; [key: string]: unknown }>>("/api/manifest/deltas"),
  },

  goals: {
    system: () =>
      apiFetch<{
        goals: Record<
          string,
          { name: string; target: string; current: Record<string, unknown> }
        >;
      }>("/api/meta/system-goals"),
  },
};

export function wsUrl(problemId: string): string {
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.hostname}:8000/ws/${problemId}`;
  }
  return `ws://acorn-api:8000/ws/${problemId}`;
}
