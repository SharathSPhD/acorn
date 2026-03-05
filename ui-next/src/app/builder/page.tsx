"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const DOMAINS = [
  "sales", "pricing", "marketing", "supply_chain", "customer",
  "finance", "operations", "human_capital", "product",
];

function statusColor(status: string): string {
  const map: Record<string, string> = {
    idle: "bg-slate-100 text-slate-600",
    perceiving: "bg-blue-100 text-blue-700",
    deciding: "bg-amber-100 text-amber-700",
    running: "bg-acorn-100 text-acorn-700",
    resting: "bg-slate-100 text-slate-500",
    paused: "bg-yellow-100 text-yellow-700",
    deferred: "bg-indigo-100 text-indigo-700",
    error: "bg-red-100 text-red-700",
    stopped: "bg-red-100 text-red-700",
  };
  return map[status] ?? "bg-slate-100 text-slate-600";
}

function statusDot(status: string): string {
  const pulsing = ["perceiving", "deciding", "running"];
  return pulsing.includes(status) ? "animate-pulse" : "";
}

function timeAgo(isoStr: string | undefined): string {
  if (!isoStr) return "--";
  const diff = Date.now() - new Date(isoStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m ago`;
}

export default function BuilderPage() {
  const queryClient = useQueryClient();
  const cortexStatus = useQuery({
    queryKey: ["cortex-status"],
    queryFn: api.cortex.status,
    refetchInterval: 3_000,
  });
  const cortexModules = useQuery({
    queryKey: ["cortex-modules"],
    queryFn: api.cortex.modules,
    refetchInterval: 3_000,
  });
  const cortexLog = useQuery({
    queryKey: ["cortex-log"],
    queryFn: () => api.cortex.broadcastLog(20),
    refetchInterval: 5_000,
  });
  const status = useQuery({
    queryKey: ["builder-status"],
    queryFn: api.builder.status,
    refetchInterval: 3_000,
  });
  const history = useQuery({
    queryKey: ["builder-history"],
    queryFn: api.builder.history,
    refetchInterval: 10_000,
  });
  const thoughts = useQuery({
    queryKey: ["builder-thoughts"],
    queryFn: api.builder.thoughts,
    refetchInterval: 5_000,
  });

  const cortexStartMut = useMutation({
    mutationFn: api.cortex.start,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["cortex-status"] }),
  });
  const cortexStopMut = useMutation({
    mutationFn: api.cortex.stop,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["cortex-status"] }),
  });
  const startMutation = useMutation({
    mutationFn: api.builder.startSprint,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["builder-status"] }),
  });
  const pauseMutation = useMutation({
    mutationFn: api.builder.pause,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["builder-status"] }),
  });
  const resumeMutation = useMutation({
    mutationFn: api.builder.resume,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["builder-status"] }),
  });
  const stopMutation = useMutation({
    mutationFn: api.builder.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["builder-status"] });
      queryClient.invalidateQueries({ queryKey: ["builder-thoughts"] });
    },
  });

  const s = status.data;
  const h = history.data;
  const cb = s?.circuit_breaker;
  const sprints = h?.recent_sprints ?? [];
  const thoughtsList = thoughts.data?.thoughts ?? [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">CORTEX+</h1>
        <p className="page-subtitle">
          Cognitive kernel with Global Workspace Theory. 7 specialist modules
          compete to broadcast actions for autonomous self-improvement.
        </p>
      </div>

      {/* Status Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <MetricCard
          label="Cortex Status"
          value={s?.status?.toUpperCase() ?? "--"}
          subtext={s?.last_action ? `Last: ${s.last_action}` : undefined}
          icon={
            <div className={`inline-flex items-center justify-center h-5 w-5 rounded-full ${statusColor(s?.status ?? "idle")}`}>
              <div className={`h-2 w-2 rounded-full bg-current ${statusDot(s?.status ?? "idle")}`} />
            </div>
          }
        />
        <MetricCard
          label="Cycle Count"
          value={s?.cycle_count ?? h?.sprint_count ?? 0}
          subtext={s?.last_action_time ? timeAgo(s.last_action_time) : undefined}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg>}
        />
        <MetricCard
          label="Total Kernels"
          value={h?.total_kernels ?? h?.total_skills ?? 0}
          subtext={`${h?.total_commits ?? 0} commits`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
        />
        <MetricCard
          label="Circuit Breaker"
          value={cb?.state?.toUpperCase() ?? "CLOSED"}
          subtext={`${cb?.consecutive_failures ?? 0} consecutive failures`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>}
        />
      </div>

      {/* Module Salience + Controls */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-8">
        <Card className="lg:col-span-2">
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Module Salience
            </h2>
            <div className="flex items-center gap-2">
              <div className={`h-2.5 w-2.5 rounded-full ${cortexStatus.data?.running ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
              <span className="text-xs text-slate-500">{cortexStatus.data?.running ? "Running" : "Stopped"}</span>
              {cortexStatus.data?.current_broadcast && (
                <Badge variant="secondary">
                  {cortexStatus.data.current_broadcast.module}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(cortexModules.data ?? []).map((m) => (
                <div key={m.module} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-slate-600 w-28 truncate capitalize">
                    {m.module}
                  </span>
                  <div className="flex-1 h-4 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        m.salience > 0.7
                          ? "bg-acorn-600"
                          : m.salience > 0.3
                            ? "bg-amber-400"
                            : "bg-slate-300"
                      }`}
                      style={{ width: `${Math.max(m.salience * 100, 2)}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-slate-500 w-10 text-right">
                    {m.salience.toFixed(2)}
                  </span>
                </div>
              ))}
              {(!cortexModules.data || cortexModules.data.length === 0) && (
                <p className="text-sm text-slate-400 py-4">Start CORTEX+ to see module salience.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Controls */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Controls</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex gap-2">
                <button
                  className="flex-1 rounded-lg bg-acorn-600 px-3 py-2 text-sm font-medium text-white hover:bg-acorn-700 disabled:opacity-50 transition-colors"
                  onClick={() => cortexStartMut.mutate()}
                  disabled={cortexStartMut.isPending || cortexStatus.data?.running}
                >
                  Start CORTEX+
                </button>
                <button
                  className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                  onClick={() => cortexStopMut.mutate()}
                  disabled={cortexStopMut.isPending || !cortexStatus.data?.running}
                >
                  Stop CORTEX+
                </button>
              </div>
              <div className="border-t border-slate-100 pt-3">
                <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Sprint Controls</p>
                <div className="flex gap-2 flex-wrap">
                  <button
                    className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors"
                    onClick={() => startMutation.mutate()}
                    disabled={startMutation.isPending}
                  >
                    {startMutation.isPending ? "Starting..." : "Start Sprint"}
                  </button>
                  <button
                    className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50 transition-colors"
                    onClick={() => pauseMutation.mutate()}
                    disabled={pauseMutation.isPending}
                  >
                    Pause
                  </button>
                  <button
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                    onClick={() => resumeMutation.mutate()}
                    disabled={resumeMutation.isPending}
                  >
                    Resume
                  </button>
                </div>
              </div>
              <div className="border-t border-slate-100 pt-3">
                <button
                  className="w-full rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
                  onClick={() => {
                    if (confirm("Stop everything? This will halt CORTEX+ and clean up all harness containers.")) {
                      stopMutation.mutate();
                    }
                  }}
                  disabled={stopMutation.isPending}
                >
                  {stopMutation.isPending ? "Shutting down..." : "Emergency Stop (Kill All)"}
                </button>
              </div>
              {stopMutation.isSuccess && (
                <div className="rounded-lg bg-red-50 border border-red-200 p-2">
                  <p className="text-xs text-red-700 font-medium">All processes stopped.</p>
                </div>
              )}
              {s?.last_action_result && (
                <div className="rounded-lg bg-slate-50 p-2">
                  <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Last Result</p>
                  <p className="text-xs text-slate-700 font-mono">{s.last_action_result}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Broadcast Log + Domain Coverage */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Broadcast Log</h2>
          </CardHeader>
          <CardContent>
            {cortexLog.data && cortexLog.data.length > 0 ? (
              <div className="max-h-56 overflow-y-auto space-y-1 font-mono text-xs">
                {[...cortexLog.data].reverse().map((entry, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-2 py-1 rounded hover:bg-slate-50"
                  >
                    <span className="text-slate-400 shrink-0">
                      {new Date(entry.timestamp * 1000).toLocaleTimeString()}
                    </span>
                    <span className={`font-medium shrink-0 ${entry.salience > 0.5 ? "text-acorn-700" : "text-slate-600"}`}>
                      {entry.module}
                    </span>
                    <span className="text-slate-500 truncate">{entry.action_type}</span>
                    <span className="text-slate-400 ml-auto shrink-0">
                      {entry.salience.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 py-2">
                No broadcasts yet. Start CORTEX+ to begin the cognitive loop.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Domain Coverage</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {DOMAINS.map((d) => {
                const baseline = h?.domain_baselines?.[d];
                const pct = baseline != null ? Math.round(baseline * 100) : 0;
                return (
                  <div key={d}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs font-medium text-slate-700 capitalize">
                        {d.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-slate-500">
                        {baseline != null ? `${(baseline * 100).toFixed(0)}%` : "--"}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full bg-acorn-500 transition-all"
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Thoughts log */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Cortex Thoughts
            {thoughts.data && (
              <span className="ml-2 text-xs text-slate-400 font-normal">
                ({thoughts.data.total} total, showing last {thoughtsList.length})
              </span>
            )}
          </h2>
        </CardHeader>
        <CardContent>
          {thoughtsList.length > 0 ? (
            <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-xs">
              {[...thoughtsList].reverse().map((t, i) => {
                const isError = t.toLowerCase().includes("error") || t.toLowerCase().includes("failed");
                const isSuccess = t.toLowerCase().includes("result: ") && !isError;
                const isDecision = t.toLowerCase().includes("llm chose") || t.toLowerCase().includes("executing:");
                return (
                  <div
                    key={i}
                    className={`px-2 py-1 rounded ${
                      isError ? "bg-red-50 text-red-700" :
                      isSuccess ? "bg-emerald-50 text-emerald-700" :
                      isDecision ? "bg-blue-50 text-blue-700" :
                      "text-slate-600"
                    }`}
                  >
                    {t}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4">No thoughts recorded yet. Start CORTEX+ to begin autonomous operation.</p>
          )}
        </CardContent>
      </Card>

      {/* Action history */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Action History
            {h && <span className="ml-2 text-xs text-slate-400 font-normal">({h.sprint_count} cycles)</span>}
          </h2>
        </CardHeader>
        <CardContent>
          {sprints.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Cycle</th>
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Time</th>
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Action</th>
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Summary</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {[...sprints].reverse().map((sp, idx) => (
                    <tr key={idx} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="py-2 px-3 font-mono text-xs">#{sp.sprint_number}</td>
                      <td className="py-2 px-3 text-xs text-slate-600">{timeAgo(sp.started_at)}</td>
                      <td className="py-2 px-3 text-xs">
                        <span className="font-medium text-slate-800">{sp.action ?? "unknown"}</span>
                      </td>
                      <td className="py-2 px-3 text-xs text-slate-600 max-w-xs truncate">
                        {sp.summary ?? "--"}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {sp.success ? (
                          <Badge variant="success">Pass</Badge>
                        ) : (
                          <Badge variant="danger">Fail</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4">No actions recorded yet. Start CORTEX+ or trigger a sprint.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
