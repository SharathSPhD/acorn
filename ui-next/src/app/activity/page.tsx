"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { StatusBadge, Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

const REFRESH_INTERVAL = 4_000;

function timeAgo(isoStr: string | null | undefined): string {
  if (!isoStr) return "--";
  const diff = Date.now() - new Date(isoStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m ago`;
}

function formatBroadcastTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ActivityPage() {
  const agents = useQuery({
    queryKey: ["agents-status"],
    queryFn: api.agents.status,
    refetchInterval: REFRESH_INTERVAL,
  });
  const broadcastLog = useQuery({
    queryKey: ["cortex-broadcast-log"],
    queryFn: () => api.cortex.broadcastLog(20),
    refetchInterval: REFRESH_INTERVAL,
  });
  const problems = useQuery({
    queryKey: ["problems-activity"],
    queryFn: api.problems.list,
    refetchInterval: REFRESH_INTERVAL,
  });
  const kernels = useQuery({
    queryKey: ["kernels-activity"],
    queryFn: () => api.kernels.list(),
    refetchInterval: REFRESH_INTERVAL,
  });

  const recentBroadcasts = (broadcastLog.data ?? []).slice(0, 10);
  const recentProblems = (problems.data ?? [])
    .sort((a, b) => new Date(b.updated_at ?? b.created_at).getTime() - new Date(a.updated_at ?? a.created_at).getTime())
    .slice(0, 10);

  const totalKernels = kernels.data?.length ?? 0;
  const probationaryKernels = kernels.data?.filter((k) => k.status === "probationary").length ?? 0;
  const permanentKernels = kernels.data?.filter((k) => k.status === "permanent").length ?? 0;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Live Activity</h1>
        <p className="page-subtitle">
          Real-time view of ACORN operations — containers, cognitive broadcasts, and problem processing.
        </p>
      </div>

      {/* Kernel Grove Live Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-8">
        <MetricCard
          label="Total Kernels"
          value={totalKernels}
          subtext="In Kernel Grove"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          }
        />
        <MetricCard
          label="Permanent"
          value={permanentKernels}
          subtext="Promoted kernels"
          icon={
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          }
        />
        <MetricCard
          label="Probationary"
          value={probationaryKernels}
          subtext="Under evaluation"
          icon={
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mb-8">
        {/* Running Harness Containers */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Running Harness Containers</h2>
            <Badge variant={agents.data && agents.data.length > 0 ? "success" : "secondary"}>
              {agents.data?.length ?? 0} active
            </Badge>
          </CardHeader>
          <CardContent>
            {agents.data && agents.data.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {agents.data.map((agent) => (
                  <div
                    key={agent.agent_id}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 transition-colors ${
                      agent.status === "running" ? "bg-acorn-50/60 animate-pulse" : "bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                          agent.status === "running" ? "bg-emerald-500" : "bg-slate-300"
                        }`}
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {agent.container_id ? agent.container_id.slice(0, 12) : agent.agent_id}
                        </p>
                        <p className="text-xs text-slate-500">
                          {agent.role}
                          {agent.problem_uuid && (
                            <span className="ml-1">· {agent.problem_uuid.slice(0, 8)}</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={agent.status} />
                      <span className="text-xs text-slate-400">{timeAgo(agent.last_seen)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 py-4">
                {agents.isLoading ? "Loading agents..." : "No harness containers running."}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Live CORTEX+ GWT Broadcast */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Live CORTEX+ GWT Broadcast</h2>
            <Badge variant="info">Last 10</Badge>
          </CardHeader>
          <CardContent>
            {recentBroadcasts.length > 0 ? (
              <div className="space-y-1 max-h-56 overflow-y-auto font-mono text-xs">
                {recentBroadcasts.map((entry, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-3 px-2 py-1.5 rounded transition-colors ${
                      i === 0 ? "bg-acorn-50 animate-pulse" : "hover:bg-slate-50"
                    }`}
                  >
                    <span className="text-slate-400 shrink-0 w-16">
                      {formatBroadcastTime(entry.timestamp)}
                    </span>
                    <span
                      className={`font-medium shrink-0 ${
                        entry.salience > 0.5 ? "text-acorn-700" : "text-slate-600"
                      }`}
                    >
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
              <p className="text-sm text-slate-500 py-4">
                {broadcastLog.isLoading ? "Loading broadcast log..." : "No broadcasts yet. Start CORTEX+ to see activity."}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Problem Activity - Timeline */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">Recent Problem Activity</h2>
          <Link href="/gallery" className="text-xs text-acorn-600 hover:text-acorn-700 font-medium">
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {recentProblems.length > 0 ? (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-200" />
              <div className="space-y-0">
                {recentProblems.map((p, i) => (
                  <Link
                    key={p.id}
                    href={`/problems/${p.id}`}
                    className="relative flex items-start gap-4 py-3 pl-10 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors"
                  >
                    <div
                      className={`absolute left-2.5 h-3 w-3 rounded-full border-2 border-white ${
                        p.status === "active" ? "bg-amber-400 animate-pulse" : p.status === "complete" ? "bg-emerald-500" : "bg-slate-300"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{p.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {formatDate(p.updated_at ?? p.created_at)}
                      </p>
                    </div>
                    <StatusBadge status={p.status} />
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4">
              {problems.isLoading ? "Loading problems..." : "No problems yet. Submit one to get started."}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Auto-refresh indicator */}
      <div className="mt-6 flex items-center gap-2 text-xs text-slate-400">
        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Auto-refreshing every {REFRESH_INTERVAL / 1000}s
      </div>
    </div>
  );
}
