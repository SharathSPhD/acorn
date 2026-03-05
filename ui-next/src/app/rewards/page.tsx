"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function healthBand(rolling30d: number): string {
  if (rolling30d > 20) return "border-l-4 border-l-emerald-500";
  if (rolling30d >= 0) return "border-l-4 border-l-amber-400";
  return "border-l-4 border-l-red-500";
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function RewardsPage() {
  const scores = useQuery({
    queryKey: ["role-scores"],
    queryFn: api.rewards.roleScores,
    refetchInterval: 10_000,
  });
  const events = useQuery({
    queryKey: ["reward-events"],
    queryFn: () => api.rewards.events(30),
    refetchInterval: 5_000,
  });
  const goals = useQuery({
    queryKey: ["system-goals"],
    queryFn: api.goals.system,
    refetchInterval: 30_000,
  });

  const goalEntries = goals.data ? Object.entries(goals.data.goals) : [];
  const totalPoints = scores.data?.reduce((sum, r) => sum + r.cumulative_points, 0) ?? 0;
  const topRole = scores.data?.reduce((best, r) =>
    r.cumulative_points > (best?.cumulative_points ?? -Infinity) ? r : best,
    scores.data[0]
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Goal-Reward System</h1>
        <p className="page-subtitle">
          Four-layer feedback stack tracking agent performance, learning, and constitutional alignment.
        </p>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <MetricCard
          label="Total Reward Points"
          value={totalPoints}
          subtext={`${scores.data?.length ?? 0} active roles`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>}
        />
        <MetricCard
          label="Top Role"
          value={topRole?.role ?? "--"}
          subtext={topRole ? `${topRole.cumulative_points} pts` : undefined}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.996.178-1.768.832-2.078 1.67m16.656 0c.31-.838 1.082-1.492 2.078-1.67M6.75 7.5l4.497-2.248a.455.455 0 01.406 0L16.15 7.5" /></svg>}
        />
        <MetricCard
          label="Recent Events"
          value={events.data?.length ?? "--"}
          subtext="last 30 events"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <MetricCard
          label="System Goals"
          value={goalEntries.length}
          subtext="tracked objectives"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 3v1.5M3 21v-6m0 0l2.77-.693a9 9 0 016.208.682l.108.054a9 9 0 006.086.71l3.114-.732a48.524 48.524 0 01-.005-10.499l-3.11.732a9 9 0 01-6.085-.711l-.108-.054a9 9 0 00-6.208-.682L3 4.5M3 15V4.5" /></svg>}
        />
      </div>

      {/* System Goals */}
      {goalEntries.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">System Goals</h2>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {goalEntries.map(([key, goal]) => (
                <div key={key} className="rounded-lg border border-slate-100 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-400">{key}</span>
                  </div>
                  <p className="text-sm font-semibold text-slate-900 mb-2">{goal.name}</p>
                  <div className="space-y-1">
                    {Object.entries(goal.current).map(([metric, val]) => (
                      <div key={metric} className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">{metric.replace(/_/g, " ")}</span>
                        <span className="text-xs font-mono font-bold text-slate-800">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 pt-2 border-t border-slate-50">
                    <span className="text-[10px] text-slate-400">Target: {goal.target}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      {goals.isLoading && (
        <Card className="mb-8">
          <CardContent>
            <p className="text-sm text-slate-400 py-4">Loading system goals...</p>
          </CardContent>
        </Card>
      )}

      {/* Role Scores */}
      <h2 className="text-sm font-semibold text-slate-900 mb-3">Role Health</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        {scores.data?.map((s) => (
          <Card key={s.role} className={healthBand(s.rolling_30d_points)}>
            <CardContent className="py-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-semibold text-slate-900">
                  {s.role}
                </span>
                <span className="text-lg font-bold text-slate-800">
                  {s.cumulative_points}
                </span>
              </div>
              <div className="flex gap-4 text-xs text-slate-500">
                <span>30d: <span className={s.rolling_30d_points > 0 ? "text-emerald-600" : s.rolling_30d_points < 0 ? "text-red-600" : ""}>{s.rolling_30d_points > 0 ? "+" : ""}{s.rolling_30d_points}</span></span>
                <span>{s.problems_contributed} problems</span>
              </div>
            </CardContent>
          </Card>
        ))}
        {scores.data?.length === 0 && (
          <div className="col-span-full text-center py-8">
            <p className="text-sm text-slate-500">No role scores yet.</p>
            <p className="text-xs text-slate-400 mt-1">Rewards will appear as problems are solved and agents accumulate performance data.</p>
          </div>
        )}
      </div>

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Recent Reward Events
          </h2>
        </CardHeader>
        <CardContent>
          {events.data && events.data.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {events.data.map((ev) => (
                <div
                  key={ev.id}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50"
                >
                  <span
                    className={`inline-flex items-center justify-center h-7 w-7 rounded-full text-xs font-bold ${
                      ev.points > 0
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {ev.points > 0 ? `+${ev.points}` : ev.points}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-800">
                        {ev.signal}
                      </span>
                      <Badge variant="secondary">{ev.role}</Badge>
                    </div>
                    {ev.rationale && (
                      <p className="text-xs text-slate-500 truncate">
                        {ev.rationale}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">
                    {timeAgo(ev.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-slate-500">No reward events yet.</p>
              <p className="text-xs text-slate-400 mt-1">Events are recorded as agents complete tasks and receive feedback.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
