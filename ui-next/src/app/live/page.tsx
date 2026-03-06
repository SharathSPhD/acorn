"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, truncateId } from "@/lib/utils";
import Link from "next/link";

const moduleColors: Record<string, { bg: string; bar: string; glow: string }> = {
  planning: { bg: "bg-blue-50", bar: "bg-blue-500", glow: "shadow-lg shadow-blue-500/50" },
  critic: { bg: "bg-red-50", bar: "bg-red-500", glow: "shadow-lg shadow-red-500/50" },
  metacognition: { bg: "bg-purple-50", bar: "bg-purple-500", glow: "shadow-lg shadow-purple-500/50" },
  perception: { bg: "bg-amber-50", bar: "bg-amber-500", glow: "shadow-lg shadow-amber-500/50" },
  memory: { bg: "bg-green-50", bar: "bg-green-500", glow: "shadow-lg shadow-green-500/50" },
  curiosity: { bg: "bg-yellow-50", bar: "bg-yellow-500", glow: "shadow-lg shadow-yellow-500/50" },
  social: { bg: "bg-pink-50", bar: "bg-pink-500", glow: "shadow-lg shadow-pink-500/50" },
};

const modules = [
  "planning",
  "critic",
  "metacognition",
  "perception",
  "memory",
  "curiosity",
  "social",
];

export default function LivePage() {
  // GWT Cognitive State - 5s poll
  const cortexStatus = useQuery({
    queryKey: ["cortex-status"],
    queryFn: api.cortex.status,
    refetchInterval: 5_000,
  });

  // Broadcast log for GWT state
  const broadcastLog = useQuery({
    queryKey: ["broadcast-log"],
    queryFn: () => api.cortex.broadcastLog(50),
    refetchInterval: 5_000,
  });

  // Manifest deltas for planning indicator
  const manifestDeltas = useQuery({
    queryKey: ["manifest-deltas"],
    queryFn: api.manifest.deltas,
    refetchInterval: 10_000,
  });

  // Telemetry for events
  const telemetry = useQuery({
    queryKey: ["telemetry"],
    queryFn: api.telemetry,
    refetchInterval: 3_000,
  });

  // Active Problems - 10s poll
  const problems = useQuery({
    queryKey: ["problems"],
    queryFn: api.problems.list,
    refetchInterval: 10_000,
  });

  // Reasoning trails for each active problem
  const activeProblems = problems.data?.filter((p) => p.status === "active") ?? [];
  const reasoningTrails = useQuery({
    queryKey: ["reasoning-trails", activeProblems.map((p) => p.id)],
    queryFn: async () => {
      const trails = await Promise.all(
        activeProblems.map((p) =>
          api.problems.reasoningTrail(p.id).catch(() => null)
        )
      );
      return trails.reduce(
        (acc, trail, idx) => {
          if (trail) acc[activeProblems[idx].id] = trail;
          return acc;
        },
        {} as Record<string, typeof trails[0]>
      );
    },
    enabled: activeProblems.length > 0,
    refetchInterval: 10_000,
  });

  // Reward Feed - 15s poll
  const rewardEvents = useQuery({
    queryKey: ["reward-events"],
    queryFn: () => api.rewards.events(20),
    refetchInterval: 15_000,
  });

  const cortex = cortexStatus.data;
  const rewards = rewardEvents.data ?? [];
  const trails = reasoningTrails.data ?? {};
  const logs = broadcastLog.data ?? [];
  const deltas = manifestDeltas.data ?? [];
  const telemetryData = telemetry.data;

  // Build salience data for bar race
  const currentBroadcast = cortex?.current_broadcast;
  const allSaliences = currentBroadcast?.all_saliences ?? {};
  const winningModule = currentBroadcast?.module ?? "";

  return (
    <div>
      <div className="page-header mb-8">
        <h1 className="page-title">Live Status</h1>
        <p className="page-subtitle">
          Real-time cognitive state, active problems, and reward signals from the ACORN network.
        </p>
      </div>

      {/* CORTEX+ GWT Salience Bar Race */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              CORTEX+ GWT Salience Race
            </h2>
            <div className="flex items-center gap-2 mt-2">
              {cortex?.running ? (
                <Badge variant="success">Running</Badge>
              ) : (
                <Badge variant="secondary">Idle</Badge>
              )}
              <span className="text-xs text-slate-400">
                Winner: <span className="font-semibold text-slate-700">{winningModule || "none"}</span>
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {modules.map((module) => {
              const salience = allSaliences[module] ?? 0;
              const isWinner = module === winningModule;
              const colors = moduleColors[module] || moduleColors["planning"];

              return (
                <div key={module} className="space-y-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-900 capitalize">
                      {module}
                    </span>
                    <span className="text-sm font-mono font-bold text-slate-700">
                      {salience.toFixed(2)}
                    </span>
                  </div>
                  <div className={`w-full h-3 rounded-full bg-slate-200 overflow-hidden transition-all ${
                    isWinner ? colors.glow : ""
                  }`}>
                    <div
                      className={`h-full transition-all duration-300 ${colors.bar} ${
                        isWinner ? "animate-pulse" : ""
                      }`}
                      style={{
                        width: `${Math.min(100, (salience / 1.0) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Multi-Domain Planning Indicator */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Manifest Domain Coverage
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Planning gaps across domains
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {deltas.map((delta, idx) => {
                const domain = (delta.domain as string) || "unknown";
                const hasGap = delta.type === "missing_kernel" || (delta.gap as number) > 0;

                return (
                  <div
                    key={idx}
                    className={`rounded-lg p-3 text-center border-2 transition-all ${
                      hasGap
                        ? "border-amber-300 bg-amber-50 animate-pulse"
                        : "border-green-300 bg-green-50"
                    }`}
                  >
                    <div className="text-xs font-semibold text-slate-900 capitalize mb-1">
                      {domain}
                    </div>
                    <div className={`text-lg font-bold ${
                      hasGap ? "text-amber-700" : "text-green-700"
                    }`}>
                      {hasGap ? "⚠" : "✓"}
                    </div>
                    <div className="text-[10px] text-slate-600 mt-1">
                      {hasGap ? "Gap" : "Satisfied"}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Event Feed */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Live Event Feed</h2>
            <span className="text-xs text-slate-400">
              {telemetryData?.total_events ?? 0} total events
            </span>
          </CardHeader>
          <CardContent>
            {(telemetryData?.recent_events ?? []).length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {(telemetryData?.recent_events ?? []).slice(0, 20).map((event, idx) => {
                  const eventData = event as any;
                  const eventType = eventData.event_type || eventData.type || "unknown";
                  let badgeColor = "bg-gray-100 text-gray-700";
                  if (eventType.includes("PASS")) badgeColor = "bg-green-100 text-green-700";
                  else if (eventType.includes("FAIL")) badgeColor = "bg-red-100 text-red-700";
                  else if (eventType.includes("PROMOTE")) badgeColor = "bg-yellow-100 text-yellow-700";
                  else if (eventType.includes("TICK")) badgeColor = "bg-blue-100 text-blue-700";

                  return (
                    <div
                      key={idx}
                      className="flex items-center gap-3 rounded-lg bg-slate-50 p-2.5 hover:bg-slate-100 transition-colors"
                    >
                      <div className="h-2 w-2 rounded-full bg-slate-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-medium text-slate-700">
                            {eventType}
                          </span>
                          <Badge variant="secondary" className={`text-[10px] ${badgeColor}`}>
                            {typeof eventData.payload === "string"
                              ? eventData.payload.substring(0, 20)
                              : "event"}
                          </Badge>
                        </div>
                        {eventData.created_at && (
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            {formatDate(eventData.created_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-4">
                No recent events
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* GWT Cognitive State */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">GWT Detailed State</h2>
            <div className="flex items-center gap-2 mt-2">
              {cortex?.running ? (
                <Badge variant="success">Running</Badge>
              ) : (
                <Badge variant="secondary">Idle</Badge>
              )}
              <span className="text-xs text-slate-400">
                Polling every {cortex?.tick_interval ?? "?"} ms
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {cortex?.current_broadcast ? (
              <div>
                <div className="mb-4">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="font-medium text-slate-900">
                      {cortex.current_broadcast.module}
                    </h3>
                    <Badge variant="default">
                      {cortex.current_broadcast.action_type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-400">Salience</span>
                    <div className="flex-1 max-w-xs h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-acorn-500 transition-all"
                        style={{
                          width: `${Math.min(
                            100,
                            (cortex.current_broadcast.salience / 1.0) * 100
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-mono text-slate-700 whitespace-nowrap">
                      {cortex.current_broadcast.salience.toFixed(2)}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-50 rounded-lg p-3 mb-4">
                  <p className="text-xs text-slate-500 mb-1 font-medium">Payload</p>
                  <pre className="text-xs text-slate-600 font-mono overflow-x-auto max-h-20 overflow-y-auto">
                    {JSON.stringify(cortex.current_broadcast.payload, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="text-sm text-slate-500">No active broadcast</p>
              </div>
            )}

            {/* Broadcast log */}
            <div className="border-t border-slate-100 pt-4">
              <p className="text-xs text-slate-500 font-medium mb-3 uppercase tracking-wider">
                Recent Broadcasts (Last 10)
              </p>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {broadcastLog.data && broadcastLog.data.length > 0 ? (
                  broadcastLog.data.map((entry, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 rounded-lg bg-slate-50 p-2.5 hover:bg-slate-100 transition-colors"
                    >
                      <div className="h-1.5 w-1.5 rounded-full bg-acorn-400 shrink-0 mt-1.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs font-medium text-slate-700">
                            {entry.module}
                          </span>
                          <Badge variant="secondary" className="text-[10px]">
                            {entry.action_type}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-500">
                          Salience: {entry.salience.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-3">
                    No broadcasts yet
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Problems */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Active Problems</h2>
            <span className="text-xs text-slate-400">
              {activeProblems.length} running
            </span>
          </CardHeader>
          <CardContent>
            {activeProblems.length > 0 ? (
              <div className="space-y-4">
                {activeProblems.map((problem) => {
                  const trail = trails[problem.id];
                  const lastSteps = trail?.steps.slice(0, 3) ?? [];

                  return (
                    <div
                      key={problem.id}
                      className="border border-slate-100 rounded-lg p-4 hover:border-slate-200 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-slate-900 truncate">
                            {problem.title}
                          </h3>
                          <p className="text-xs text-slate-500 font-mono mt-1">
                            {truncateId(problem.id, 8)}
                          </p>
                        </div>
                        <Link
                          href={`/problems/${problem.id}`}
                          className="text-xs text-acorn-600 hover:text-acorn-700 font-medium whitespace-nowrap ml-2"
                        >
                          View →
                        </Link>
                      </div>

                      {/* Reasoning steps */}
                      {lastSteps.length > 0 && (
                        <div className="bg-slate-50 rounded-lg p-3 mt-3">
                          <p className="text-xs text-slate-500 font-medium mb-2 uppercase tracking-wider">
                            Recent Reasoning
                          </p>
                          <div className="space-y-1.5">
                            {lastSteps.map((step, idx) => (
                              <div key={idx} className="text-xs">
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="font-mono text-slate-600">
                                    {step.step_type}
                                  </span>
                                  {step.confidence !== null && (
                                    <span className="text-slate-500">
                                      {(step.confidence * 100).toFixed(0)}%
                                    </span>
                                  )}
                                </div>
                                <p className="text-slate-500 line-clamp-2">
                                  {step.summary}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="text-sm text-slate-500">No active problems</p>
                <p className="text-xs text-slate-400 mt-1">
                  Submit a problem to see live activity here.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reward Feed */}
      <div>
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Reward Feed</h2>
            <span className="text-xs text-slate-400">
              Last 20 signals
            </span>
          </CardHeader>
          <CardContent>
            {rewards.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {rewards.map((event, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      "flex items-start gap-3 rounded-lg p-3 transition-colors",
                      event.points > 0
                        ? "bg-green-50 hover:bg-green-100"
                        : "bg-red-50 hover:bg-red-100"
                    )}
                  >
                    <div
                      className={cn(
                        "h-1.5 w-1.5 rounded-full shrink-0 mt-1.5",
                        event.points > 0 ? "bg-green-500" : "bg-red-500"
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className="text-xs font-medium text-slate-700">
                          {event.signal}
                        </span>
                        <Badge
                          variant="secondary"
                          className="text-[10px]"
                        >
                          {event.role}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] text-slate-600 line-clamp-1">
                          {event.rationale || "No rationale"}
                        </p>
                        <span
                          className={cn(
                            "text-xs font-bold whitespace-nowrap ml-2",
                            event.points > 0
                              ? "text-green-700"
                              : "text-red-700"
                          )}
                        >
                          {event.points > 0 ? "+" : ""}{event.points}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        {formatDate(event.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="text-sm text-slate-500">No reward signals yet</p>
                <p className="text-xs text-slate-400 mt-1">
                  Signals appear as agents solve problems and gain points.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Helper to merge class names
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
