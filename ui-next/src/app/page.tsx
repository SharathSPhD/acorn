"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { StatusBadge, Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export default function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15_000 });
  const problems = useQuery({ queryKey: ["problems"], queryFn: api.problems.list });
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents.status });
  const kernels = useQuery({ queryKey: ["kernels"], queryFn: () => api.kernels.list() });
  const cortexStatus = useQuery({ queryKey: ["cortex-status"], queryFn: api.cortex.status, refetchInterval: 5_000 });
  const manifestDeltas = useQuery({ queryKey: ["manifest-deltas"], queryFn: api.manifest.deltas, refetchInterval: 30_000 });
  const roleScores = useQuery({ queryKey: ["role-scores"], queryFn: api.rewards.roleScores, refetchInterval: 15_000 });

  const activeCount = problems.data?.filter((p) => p.status === "active").length ?? 0;
  const completeCount = problems.data?.filter((p) => p.status === "complete").length ?? 0;
  const agentCount = agents.data?.length ?? 0;
  const kernelCount = kernels.data?.length ?? 0;
  const permanentKernels = kernels.data?.filter((k) => k.status === "permanent").length ?? 0;

  const cortexRunning = cortexStatus.data?.running ?? false;
  const deltasCount = manifestDeltas.data?.length ?? 0;
  const totalRewardPoints = roleScores.data?.reduce((sum, r) => sum + r.cumulative_points, 0) ?? 0;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Command Center</h1>
        <p className="page-subtitle">
          ACORN system overview &mdash; problems, agents, kernels, and cognitive state at a glance.
        </p>
      </div>

      {/* Health bar */}
      <div className="mb-6 flex items-center gap-3 rounded-lg border px-4 py-2.5 bg-white">
        <div className={`h-2.5 w-2.5 rounded-full ${health.data ? "bg-emerald-500" : "bg-red-500"}`} />
        <span className="text-sm font-medium text-slate-700">
          {health.data ? "System Healthy" : health.isLoading ? "Checking..." : "System Unreachable"}
        </span>
        {health.data && (
          <>
            <span className="text-slate-300">|</span>
            <span className="text-xs text-slate-500">
              Mode: {health.data.acorn_mode.toUpperCase()} &middot; Routing: {health.data.routing_strategy}
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-xs text-slate-500">
              CORTEX+: <span className={cortexRunning ? "text-emerald-600 font-medium" : "text-slate-400"}>{cortexRunning ? "Running" : "Stopped"}</span>
            </span>
          </>
        )}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6 mb-8">
        <MetricCard
          label="Problems"
          value={problems.data?.length ?? "--"}
          subtext={`${activeCount} active, ${completeCount} complete`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>}
        />
        <MetricCard
          label="Active Agents"
          value={agentCount}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" /></svg>}
        />
        <MetricCard
          label="Kernels"
          value={kernelCount}
          subtext={`${permanentKernels} permanent`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
        />
        <MetricCard
          label="Reward Points"
          value={totalRewardPoints}
          subtext={`${roleScores.data?.length ?? 0} roles`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>}
        />
        <MetricCard
          label="Manifest Gaps"
          value={deltasCount}
          subtext={deltasCount > 0 ? "Action needed" : "Aligned"}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>}
        />
        <MetricCard
          label="Models"
          value={health.data ? Object.keys(health.data.models).length : "--"}
          subtext={health.data?.models?.coder ?? ""}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" /></svg>}
        />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-6 mb-8">
        <Link href="/submit" className="group">
          <Card className="h-full border-2 border-dashed border-acorn-200 hover:border-acorn-400 bg-acorn-50/30">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-acorn-100 text-acorn-600 group-hover:bg-acorn-200 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">Submit</p>
              <p className="text-[10px] text-slate-500 mt-0.5">New problem</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/gallery" className="group">
          <Card className="h-full hover:border-slate-300">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600 group-hover:bg-slate-200 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">Gallery</p>
              <p className="text-[10px] text-slate-500 mt-0.5">All problems</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/kernels" className="group">
          <Card className="h-full hover:border-slate-300">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600 group-hover:bg-slate-200 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">Kernels</p>
              <p className="text-[10px] text-slate-500 mt-0.5">Reusable patterns</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/rewards" className="group">
          <Card className="h-full hover:border-slate-300">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-amber-600 group-hover:bg-amber-100 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">Rewards</p>
              <p className="text-[10px] text-slate-500 mt-0.5">GRS scores</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/builder" className="group">
          <Card className="h-full hover:border-slate-300">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.23 3.05a1 1 0 01-1.46-1.06l1-5.82-4.24-4.13a1 1 0 01.56-1.71l5.85-.85 2.62-5.3a1 1 0 011.8 0l2.62 5.3 5.85.85a1 1 0 01.56 1.71l-4.24 4.13 1 5.82a1 1 0 01-1.46 1.06l-5.23-3.05z" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">CORTEX+</p>
              <p className="text-[10px] text-slate-500 mt-0.5">Cognitive kernel</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/telemetry" className="group">
          <Card className="h-full hover:border-slate-300">
            <CardContent className="flex flex-col items-center py-6">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600 group-hover:bg-slate-200 transition-colors">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z" /></svg>
              </div>
              <p className="text-sm font-semibold text-slate-900">Telemetry</p>
              <p className="text-[10px] text-slate-500 mt-0.5">Agent metrics</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-8">
        {/* Manifest Deltas */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Manifest Alignment</h2>
            <Badge variant={deltasCount === 0 ? "success" : "warning"}>
              {deltasCount === 0 ? "Aligned" : `${deltasCount} gap${deltasCount > 1 ? "s" : ""}`}
            </Badge>
          </CardHeader>
          <CardContent>
            {manifestDeltas.data && manifestDeltas.data.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {manifestDeltas.data.slice(0, 8).map((delta, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className={`inline-block h-2 w-2 rounded-full shrink-0 ${
                      delta.type === "missing_kernel" ? "bg-amber-400" :
                      delta.type === "missing_model" ? "bg-red-400" :
                      delta.type === "missing_agent" ? "bg-indigo-400" :
                      "bg-slate-300"
                    }`} />
                    <span className="text-slate-700 truncate">
                      {delta.type?.toString().replace(/_/g, " ")}
                      {delta.domain ? `: ${delta.domain}` : ""}
                      {delta.model ? `: ${delta.model}` : ""}
                      {delta.role ? `: ${delta.role}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 py-2">
                {manifestDeltas.isLoading ? "Checking alignment..." : "All manifest targets met."}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Role Health Summary */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Role Health</h2>
            <Link href="/rewards" className="text-xs text-acorn-600 hover:text-acorn-700 font-medium">Details</Link>
          </CardHeader>
          <CardContent>
            {roleScores.data && roleScores.data.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {roleScores.data.map((r) => (
                  <div key={r.role} className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">{r.role}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono font-bold ${
                        r.rolling_30d_points > 0 ? "text-emerald-600" :
                        r.rolling_30d_points < 0 ? "text-red-600" : "text-slate-400"
                      }`}>
                        {r.rolling_30d_points > 0 ? "+" : ""}{r.rolling_30d_points}
                      </span>
                      <span className="text-[10px] text-slate-400">{r.problems_contributed}p</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 py-2">No role scores yet. Solve problems to generate rewards.</p>
            )}
          </CardContent>
        </Card>

        {/* CORTEX+ Status */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">CORTEX+ Status</h2>
            <Link href="/builder" className="text-xs text-acorn-600 hover:text-acorn-700 font-medium">Open</Link>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 mb-3">
              <div className={`h-3 w-3 rounded-full ${cortexRunning ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
              <span className="text-sm font-medium text-slate-700">
                {cortexRunning ? "Cognitive Loop Active" : "Stopped"}
              </span>
            </div>
            {cortexStatus.data?.current_broadcast ? (
              <div className="rounded-lg bg-acorn-50 border border-acorn-100 p-3">
                <p className="text-xs text-acorn-700 font-medium">
                  Broadcasting: {cortexStatus.data.current_broadcast.module}
                </p>
                <p className="text-[10px] text-acorn-500 mt-0.5">
                  Action: {cortexStatus.data.current_broadcast.action_type} &middot;
                  Salience: {cortexStatus.data.current_broadcast.salience.toFixed(2)}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                {cortexRunning ? "Waiting for next broadcast cycle..." : "Start CORTEX+ to enable autonomous operation."}
              </p>
            )}
            {cortexStatus.data && (
              <div className="mt-3 flex gap-4 text-xs text-slate-500">
                <span>Tick: {cortexStatus.data.tick_interval}s</span>
                <span>Log: {cortexStatus.data.broadcast_log_size} entries</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent problems */}
      {problems.data && problems.data.length > 0 && (
        <Card>
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-900">Recent Problems</h2>
            <Link href="/gallery" className="text-xs text-acorn-600 hover:text-acorn-700 font-medium">View all</Link>
          </div>
          <div className="divide-y divide-slate-50">
            {problems.data.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                href={`/problems/${p.id}`}
                className="flex items-center justify-between px-6 py-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={p.status} />
                  <div>
                    <p className="text-sm font-medium text-slate-900">{p.title}</p>
                    <p className="text-xs text-slate-400">{formatDate(p.created_at)}</p>
                  </div>
                </div>
                <svg className="h-4 w-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
