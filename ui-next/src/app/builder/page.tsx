"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

const DOMAINS = [
  "sales", "pricing", "marketing", "supply_chain", "customer",
  "finance", "operations", "human_capital", "product",
];

function statusColor(status: string): string {
  const map: Record<string, string> = {
    idle: "bg-slate-100 text-slate-600",
    scanning: "bg-blue-100 text-blue-700",
    synthesizing: "bg-amber-100 text-amber-700",
    running: "bg-oak-100 text-oak-700",
    reviewing: "bg-indigo-100 text-indigo-700",
    committing: "bg-emerald-100 text-emerald-700",
    resting: "bg-slate-100 text-slate-500",
    halted: "bg-red-100 text-red-700",
    stopped: "bg-slate-200 text-slate-500",
  };
  return map[status] ?? "bg-slate-100 text-slate-600";
}

function breakerBadge(state: string) {
  if (state === "halted") return <Badge variant="danger">HALTED</Badge>;
  if (state === "degraded") return <Badge variant="warning">DEGRADED</Badge>;
  return <Badge variant="success">CLOSED</Badge>;
}

export default function BuilderPage() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: ["builder-status"],
    queryFn: api.builder.status,
    refetchInterval: 5_000,
  });
  const history = useQuery({
    queryKey: ["builder-history"],
    queryFn: api.builder.history,
    refetchInterval: 15_000,
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

  const s = status.data;
  const h = history.data;
  const cb = s?.circuit_breaker;
  const sprints = h?.recent_sprints ?? [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Self-Build</h1>
        <p className="page-subtitle">
          Autonomous sprint lifecycle, skill acquisition, and release management.
        </p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <MetricCard
          label="Builder Status"
          value={s?.status?.toUpperCase() ?? "--"}
          icon={
            <div className={`inline-flex items-center justify-center h-5 w-5 rounded-full ${statusColor(s?.status ?? "idle")}`}>
              <div className={`h-2 w-2 rounded-full ${s?.status === "running" || s?.status === "synthesizing" ? "bg-current animate-pulse" : "bg-current"}`} />
            </div>
          }
        />
        <MetricCard
          label="Total Skills"
          value={h?.total_skills ?? 0}
          subtext={`${h?.total_commits ?? 0} commits`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
        />
        <MetricCard
          label="Releases"
          value={h?.release_count ?? 0}
          subtext={`${h?.stories_since_release ?? 0}/5 stories to next`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" /></svg>}
        />
        <MetricCard
          label="Circuit Breaker"
          value={cb?.state?.toUpperCase() ?? "CLOSED"}
          subtext={`${cb?.consecutive_failures ?? 0} consecutive failures`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>}
        />
      </div>

      {/* Controls + Circuit Breaker */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Controls</h2>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 flex-wrap">
              <button
                className="rounded-lg bg-oak-600 px-4 py-2 text-sm font-medium text-white hover:bg-oak-700 disabled:opacity-50 transition-colors"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending || !s?.builder_enabled}
              >
                {startMutation.isPending ? "Triggering..." : "Start Sprint"}
              </button>
              <button
                className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50 transition-colors"
                onClick={() => pauseMutation.mutate()}
                disabled={pauseMutation.isPending}
              >
                Pause
              </button>
              <button
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
              >
                Resume / Reset CB
              </button>
            </div>
            {s?.last_sprint_result && (
              <div className="mt-4 rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Last Sprint Result</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-slate-600">Passed</span>
                  <span className="font-medium text-emerald-600">{s.last_sprint_result.passed}</span>
                  <span className="text-slate-600">Failed</span>
                  <span className="font-medium text-red-500">{s.last_sprint_result.failed}</span>
                  <span className="text-slate-600">Skills</span>
                  <span className="font-medium text-oak-600">{s.last_sprint_result.skills}</span>
                  <span className="text-slate-600">Committed</span>
                  <span className="font-medium">{s.last_sprint_result.committed ? "Yes" : "No"}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Domain coverage */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Domain Coverage</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {DOMAINS.map((d) => {
                const baseline = h?.domain_baselines?.[d];
                const pct = baseline != null ? Math.round(baseline * 100) : 0;
                return (
                  <div key={d}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-700 capitalize">
                        {d.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-slate-500">
                        {baseline != null ? `${(baseline * 100).toFixed(0)}%` : "--"}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-oak-500 transition-all"
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

      {/* Sprint history */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Sprint History
            {h && <span className="ml-2 text-xs text-slate-400 font-normal">({h.sprint_count} total)</span>}
          </h2>
        </CardHeader>
        <CardContent>
          {sprints.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Sprint</th>
                    <th className="py-2 px-3 text-left text-xs font-medium text-slate-500">Started</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">Submitted</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">Passed</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">Skills</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">Committed</th>
                    <th className="py-2 px-3 text-center text-xs font-medium text-slate-500">CB State</th>
                  </tr>
                </thead>
                <tbody>
                  {[...sprints].reverse().map((sp) => (
                    <tr key={sp.sprint_number} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="py-2 px-3 font-mono text-xs">#{sp.sprint_number}</td>
                      <td className="py-2 px-3 text-xs text-slate-600">{formatDate(sp.started_at)}</td>
                      <td className="py-2 px-3 text-center">{sp.problems_submitted}</td>
                      <td className="py-2 px-3 text-center">
                        <span className={sp.problems_passed > 0 ? "text-emerald-600 font-medium" : "text-slate-400"}>
                          {sp.problems_passed}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <span className={sp.skills_ingested > 0 ? "text-oak-600 font-medium" : "text-slate-400"}>
                          {sp.skills_ingested}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        {sp.changes_committed ? (
                          <Badge variant="success">Yes</Badge>
                        ) : (
                          <span className="text-slate-400">No</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-center">{breakerBadge(sp.circuit_breaker_state)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4">No sprints recorded yet. Start a sprint to begin self-improvement.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
