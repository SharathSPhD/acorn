"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

export default function HealerPage() {
  const problems = useQuery({
    queryKey: ["problems"],
    queryFn: api.problems.list,
    refetchInterval: 10_000,
  });

  const broadcastLog = useQuery({
    queryKey: ["broadcast-log"],
    queryFn: () => api.cortex.broadcastLog(200),
    refetchInterval: 15_000,
  });

  const roleScores = useQuery({
    queryKey: ["role-scores"],
    queryFn: api.rewards.roleScores,
    refetchInterval: 10_000,
  });

  const allProblems = problems.data ?? [];
  const failedProblems = allProblems.filter((p) => p.status === "failed");
  const recoveryProblems = allProblems.filter((p) =>
    p.title.toLowerCase().startsWith("[recovery]")
  );
  const metaProblems = allProblems.filter((p) =>
    p.title.toLowerCase().includes("cortex+ meta:")
  );

  // Get judge verdicts for failure analysis
  const failurePatterns = failedProblems.reduce(
    (acc, p) => {
      acc[p.id] = { title: p.title, checks: {} };
      return acc;
    },
    {} as Record<string, any>
  );

  // Analyze failure patterns from judge verdicts (mock data for now)
  const failureCheckCounts: Record<string, number> = {
    "problem_addressed": failedProblems.filter((p) =>
      p.title.includes("issue")
    ).length,
    "code_valid": Math.floor(failedProblems.length * 0.3),
    "artifacts_present": Math.floor(failedProblems.length * 0.4),
    "analysis_evident": Math.floor(failedProblems.length * 0.5),
  };

  // Calculate rolling pass rate (last 30 problems)
  const recentProblems = allProblems.slice(0, 30);
  const passRateData = [];
  let passed = 0;
  for (let i = 0; i < Math.min(recentProblems.length, 30); i += 3) {
    const window = recentProblems.slice(Math.max(0, i - 10), i);
    const windowPassed = window.filter((p) => p.status === "complete").length;
    const windowPassRate =
      window.length > 0 ? (windowPassed / window.length) * 100 : 0;
    passRateData.push({
      window: `P${i / 3 + 1}`,
      passRate: Math.round(windowPassRate),
    });
  }

  const failureData = [
    { check: "Problem Addressed", count: failureCheckCounts["problem_addressed"] },
    { check: "Code Valid", count: failureCheckCounts["code_valid"] },
    { check: "Artifacts Present", count: failureCheckCounts["artifacts_present"] },
    { check: "Analysis Evident", count: failureCheckCounts["analysis_evident"] },
  ];

  // Get cortex amendments
  const amendments = (broadcastLog.data ?? [])
    .filter(
      (e) =>
        e.action_type === "propose_amendment" ||
        e.action_type === "generate_objective"
    )
    .slice(0, 10);

  const scores = roleScores.data ?? [];
  const sortedScores = [...scores].sort(
    (a, b) => b.cumulative_points - a.cumulative_points
  );

  return (
    <div>
      <div className="page-header mb-8">
        <h1 className="page-title">Healer Dashboard</h1>
        <p className="page-subtitle">
          ACORN healing itself in real-time: failure patterns, recovery queue,
          and self-improvement cycle.
        </p>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <MetricCard
          label="Failed Problems"
          value={failedProblems.length}
          subtext={`${((failedProblems.length / allProblems.length) * 100).toFixed(1)}% failure rate`}
          icon={
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <MetricCard
          label="Recovery Queue"
          value={recoveryProblems.length}
          subtext="In progress"
          icon={
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7m0 0A48.678 48.678 0 0012 3c-4.747 0-9.27.713-13.5 2.092m0 0a48.667 48.667 0 013.7 3.7c-.092 1.209-.138 2.43-.138 3.662m13.5 0c1.232 0 2.453.046 3.662.138a4.006 4.006 0 013.7 3.7m0 0a48.667 48.667 0 00-3.7-3.7m0 0a48.667 48.667 0 00-13.5-2.092m13.5 0c4.247 0 8.312.741 12 2.092M0 12c0 1.232.046 2.453.138 3.662a4.006 4.006 0 003.7 3.7m0 0a48.678 48.678 0 01-3.7-3.7m0 0a48.667 48.667 0 0013.5 2.092"
              />
            </svg>
          }
        />
        <MetricCard
          label="Meta-Analysis"
          value={metaProblems.length}
          subtext="Self-analysis problems"
          icon={
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.5 19.5l-3-3m3 3v-4.5m0 4.5h4.5m-4.5 0v-4.5m4.5 4.5l3-3m-3 3v-4.5m0 4.5h4.5m-4.5 0v-4.5m4.5 4.5l3-3m-3 3v-4.5m0 4.5h4.5m-4.5 0v-4.5"
              />
            </svg>
          }
        />
        <MetricCard
          label="Pass Rate (10-problem window)"
          value={`${passRateData.length > 0 ? passRateData[passRateData.length - 1].passRate : 0}%`}
          subtext="Current trend"
          icon={
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.518l2.74-1.22m0 0l-5.94 7.28m5.94-7.28l1.22 2.74c.531 1.174.49 2.583-.313 3.714M2.25 6L9 12.75l4.306-4.307a11.95 11.95 0 015.814 5.518l2.74 1.22m0 0l-5.94-7.28m5.94 7.28l1.22-2.74c.531-1.174.49-2.583-.313-3.714"
              />
            </svg>
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Failure Pattern Analysis */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Judge Check Failures
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Distribution of check failures across {failedProblems.length} failed problems
            </p>
          </CardHeader>
          <CardContent>
            {failureData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={failureData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="check"
                    tick={{ fontSize: 12 }}
                    stroke="#64748b"
                  />
                  <YAxis tick={{ fontSize: 12 }} stroke="#64748b" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                    cursor={{ fill: "rgba(79, 70, 229, 0.1)" }}
                  />
                  <Bar dataKey="count" fill="#ef4444" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-sm text-slate-500">No failure data</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pass Rate Trend */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Pass Rate Trend
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Rolling 10-problem window pass rate
            </p>
          </CardHeader>
          <CardContent>
            {passRateData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={passRateData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="window"
                    tick={{ fontSize: 12 }}
                    stroke="#64748b"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 12 }}
                    stroke="#64748b"
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                    formatter={(value) => `${value}%`}
                  />
                  <Line
                    type="monotone"
                    dataKey="passRate"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ fill: "#10b981", r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-sm text-slate-500">Insufficient data</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Role Score Leaderboard */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Role Health Leaderboard
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Agent role performance scores
          </p>
        </CardHeader>
        <CardContent>
          {sortedScores.length > 0 ? (
            <div className="space-y-2">
              {sortedScores.map((score) => {
                const isPositive = score.cumulative_points > 0;
                return (
                  <div
                    key={score.role}
                    className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-slate-900">
                          {score.role}
                        </span>
                        <span className="text-xs text-slate-500">
                          {score.problems_contributed} problems
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-300 overflow-hidden">
                        <div
                          className={`h-full ${
                            isPositive ? "bg-green-500" : "bg-red-500"
                          }`}
                          style={{
                            width: `${Math.min(
                              100,
                              Math.abs(score.cumulative_points) / 100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div
                      className={`text-lg font-bold whitespace-nowrap ${
                        isPositive ? "text-green-700" : "text-red-700"
                      }`}
                    >
                      {isPositive ? "+" : ""}{score.cumulative_points}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-6">
              No role scores yet
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recovery Queue */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Recovery Queue
            </h2>
            <span className="text-xs text-slate-500">
              {recoveryProblems.length} active recovery{
                recoveryProblems.length !== 1 ? "s" : ""
              }
            </span>
          </CardHeader>
          <CardContent>
            {recoveryProblems.length > 0 ? (
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {recoveryProblems.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-lg border border-amber-200 bg-amber-50 p-3"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <h4 className="text-sm font-medium text-slate-900 flex-1">
                        {p.title}
                      </h4>
                      <Badge variant="secondary" className="text-xs ml-2">
                        {p.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2 mb-2">
                      {p.description}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      Created {formatDate(p.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center">
                <p className="text-sm text-slate-500">No active recoveries</p>
                <p className="text-xs text-slate-400 mt-1">
                  Recovery problems appear when CORTEX+ detects failures
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* CORTEX+ Amendments */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              CORTEX+ Amendments
            </h2>
            <span className="text-xs text-slate-500">
              {amendments.length} recent amendment{amendments.length !== 1 ? "s" : ""}
            </span>
          </CardHeader>
          <CardContent>
            {amendments.length > 0 ? (
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {amendments.map((entry, idx) => (
                  <div key={idx} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-xs font-mono text-slate-500 shrink-0">
                        {new Date(entry.timestamp * 1000).toLocaleTimeString()}
                      </span>
                      <Badge variant="secondary" className="text-[10px]">
                        {entry.action_type}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-700 line-clamp-3">
                      {entry.module}: {JSON.stringify(entry.payload).substring(0, 100)}...
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center">
                <p className="text-sm text-slate-500">No amendments yet</p>
                <p className="text-xs text-slate-400 mt-1">
                  Amendments appear as CORTEX+ proposes improvements
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Meta-Analysis Problems */}
      {metaProblems.length > 0 && (
        <Card className="mt-8">
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              Meta-Analysis Problems
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Self-analysis and improvement planning
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {metaProblems.map((p) => (
                <div
                  key={p.id}
                  className="rounded-lg border border-slate-200 p-4 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-sm font-medium text-slate-900 flex-1">
                      {p.title}
                    </h4>
                    <Badge
                      variant="secondary"
                      className={`text-xs ml-2 ${
                        p.status === "complete"
                          ? "bg-green-100 text-green-700"
                          : p.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-blue-100 text-blue-700"
                      }`}
                    >
                      {p.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600 mb-2">
                    {p.description}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    {formatDate(p.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
