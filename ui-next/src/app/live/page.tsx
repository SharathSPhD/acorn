"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, truncateId } from "@/lib/utils";
import Link from "next/link";

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
    queryFn: () => api.cortex.broadcastLog(10),
    refetchInterval: 5_000,
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

  return (
    <div>
      <div className="page-header mb-8">
        <h1 className="page-title">Live Status</h1>
        <p className="page-subtitle">
          Real-time cognitive state, active problems, and reward signals from the ACORN network.
        </p>
      </div>

      {/* GWT Cognitive State */}
      <div className="mb-8">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">GWT Cognitive State</h2>
            <div className="flex items-center gap-2">
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
