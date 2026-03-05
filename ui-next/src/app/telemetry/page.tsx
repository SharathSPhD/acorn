"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export default function TelemetryPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15_000 });
  const telemetry = useQuery({ queryKey: ["telemetry"], queryFn: api.telemetry, refetchInterval: 10_000 });
  const models = useQuery({ queryKey: ["models"], queryFn: api.agents.models });
  const healthMetrics = useQuery({ queryKey: ["health-metrics"], queryFn: api.meta.healthMetrics, refetchInterval: 30_000 });
  const manifestStatus = useQuery({ queryKey: ["manifest-status"], queryFn: api.manifest.status, refetchInterval: 30_000 });

  const t = telemetry.data;
  const h = health.data;
  const hm = healthMetrics.data;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Telemetry & Observability</h1>
        <p className="page-subtitle">
          Agent performance metrics, model routing, system health, and manifest alignment.
        </p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 mb-8">
        <MetricCard
          label="Total Events"
          value={t?.total_events ?? "--"}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>}
        />
        <MetricCard
          label="Escalation Rate"
          value={t ? `${t.escalation_rate_pct.toFixed(1)}%` : "--"}
          subtext={`${t?.total_escalations ?? 0} escalations`}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" /></svg>}
        />
        <MetricCard
          label="Judge Pass Rate (7d)"
          value={hm ? `${(hm.judge_pass_rate_7d * 100).toFixed(0)}%` : "--"}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <MetricCard
          label="Kernel Promotion (7d)"
          value={hm ? `${(hm.kernel_promotion_rate_7d * 100).toFixed(0)}%` : "--"}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
        />
        <MetricCard
          label="System Mode"
          value={h?.acorn_mode?.toUpperCase() ?? "--"}
          subtext={h?.routing_strategy ?? ""}
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg>}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mb-8">
        {/* Events by type */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Events by Type</h2>
          </CardHeader>
          <CardContent>
            {t?.events_by_type && Object.keys(t.events_by_type).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(t.events_by_type)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => {
                    const maxCount = Math.max(...Object.values(t.events_by_type));
                    const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
                    return (
                      <div key={type}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-slate-700">{type}</span>
                          <span className="text-xs text-slate-500">{count}</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className="h-2 rounded-full bg-acorn-500 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="text-sm text-slate-500">No events recorded yet.</p>
                <p className="text-xs text-slate-400 mt-1">Events appear as agents solve problems and interact with the system.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Model routing */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Model Routing</h2>
          </CardHeader>
          <CardContent>
            {models.data ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Base Models</p>
                  <div className="space-y-2">
                    {Object.entries(models.data.models).map(([role, model]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className="text-sm text-slate-600 capitalize">{role}</span>
                        <code className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 font-mono">{model}</code>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="border-t border-slate-100 pt-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Role Assignments</p>
                  <div className="space-y-2">
                    {Object.entries(models.data.role_routing).map(([role, model]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">{role}</span>
                        <code className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 font-mono">{model}</code>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Loading model configuration...</p>
            )}
          </CardContent>
        </Card>

        {/* Manifest alignment */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">Manifest Alignment</h2>
          </CardHeader>
          <CardContent>
            {manifestStatus.data ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Desired State (Domains)</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(manifestStatus.data.desired as { domains?: Array<{ name: string }> })?.domains?.map((d: { name: string }) => (
                      <span key={d.name} className="rounded bg-acorn-50 border border-acorn-200 px-2 py-0.5 text-xs text-acorn-700">
                        {d.name}
                      </span>
                    )) ?? (
                      <p className="text-xs text-slate-400">No domain targets defined.</p>
                    )}
                  </div>
                </div>
                <div className="border-t border-slate-100 pt-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Actual Capabilities</p>
                  <div className="space-y-1.5">
                    {Object.entries(manifestStatus.data.actual).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between">
                        <span className="text-xs text-slate-600 capitalize">{key.replace(/_/g, " ")}</span>
                        <span className="text-xs font-mono text-slate-700">
                          {Array.isArray(val) ? val.length : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center">
                <p className="text-sm text-slate-500">Loading manifest data...</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Feature flags */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">System Configuration</h2>
          </CardHeader>
          <CardContent>
            {h?.feature_flags ? (
              <div className="space-y-3">
                {Object.entries(h.feature_flags).map(([flag, enabled]) => (
                  <div key={flag} className="flex items-center justify-between">
                    <span className="text-sm text-slate-700">
                      {flag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <Badge variant={enabled ? "success" : "secondary"}>
                      {enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                ))}
                {h && (
                  <div className="border-t border-slate-100 pt-3 mt-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">Max Agents/Problem</span>
                        <span className="text-sm font-medium text-slate-800">{h.max_agents_per_problem}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">Max Concurrent Problems</span>
                        <span className="text-sm font-medium text-slate-800">{h.max_concurrent_problems}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">API Key Present</span>
                        <Badge variant={h.api_key_present ? "success" : "secondary"}>
                          {h.api_key_present ? "Yes" : "No"}
                        </Badge>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Loading configuration...</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent events */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">Recent Events</h2>
        </CardHeader>
        <CardContent>
          {t?.recent_events && t.recent_events.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {t.recent_events.map((ev, i) => (
                <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-slate-50">
                  <div className="h-1.5 w-1.5 rounded-full bg-acorn-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">
                      {ev.event_type as string}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      {ev.agent_id as string} &middot; {formatDate(ev.created_at as string)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-slate-500">No recent events.</p>
              <p className="text-xs text-slate-400 mt-1">Events appear as agents run problems and interact with the system.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
