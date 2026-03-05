"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

const STEP_COLORS: Record<string, string> = {
  init: "bg-blue-500/10 border-blue-500/30",
  decomposition: "bg-purple-500/10 border-purple-500/30",
  task_creation: "bg-indigo-500/10 border-indigo-500/30",
  agent_spawn: "bg-green-500/10 border-green-500/30",
  poll_complete: "bg-yellow-500/10 border-yellow-500/30",
  judge: "bg-orange-500/10 border-orange-500/30",
  conclusion: "bg-emerald-500/10 border-emerald-500/30",
  generic: "bg-zinc-500/10 border-zinc-500/30",
};

export default function ReasoningTrailPage() {
  const { id } = useParams<{ id: string }>();

  const trail = useQuery({
    queryKey: ["reasoning-trail", id],
    queryFn: () => api.problems.reasoningTrail(id),
    refetchInterval: 10_000,
  });

  const problem = useQuery({
    queryKey: ["problem", id],
    queryFn: () => api.problems.get(id),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href={`/problems/${id}`} className="text-sm text-zinc-400 hover:text-white">
            &larr; Back to problem
          </Link>
          <h1 className="text-2xl font-bold mt-1">Reasoning Trail</h1>
          {problem.data && (
            <p className="text-zinc-400 text-sm mt-1">{problem.data.title}</p>
          )}
        </div>
        <div className="text-sm text-zinc-500">
          {trail.data?.count ?? 0} steps recorded
        </div>
      </div>

      {trail.isLoading && <p className="text-zinc-500">Loading...</p>}

      {trail.data && trail.data.steps.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-zinc-500">
            No reasoning steps recorded yet.
            {problem.data?.status === "active" && " Steps will appear as the pipeline progresses."}
          </CardContent>
        </Card>
      )}

      <div className="relative">
        {trail.data && trail.data.steps.length > 0 && (
          <div className="absolute left-6 top-0 bottom-0 w-px bg-zinc-700" />
        )}

        <div className="space-y-4">
          {trail.data?.steps.map((step, i) => {
            const colors = STEP_COLORS[step.step_type] || STEP_COLORS.generic;
            return (
              <div key={step.id} className="relative pl-14">
                <div className="absolute left-4 top-4 w-4 h-4 rounded-full bg-zinc-800 border-2 border-zinc-500 z-10" />
                <Card className={`border ${colors}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-zinc-500">#{i + 1}</span>
                        <StatusBadge status={step.step_type} />
                        <span className="text-sm text-zinc-400">by {step.agent_id}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        {step.confidence !== null && (
                          <span className="text-xs text-zinc-500">
                            confidence: {(step.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                        <span className="text-xs text-zinc-500">
                          {formatDate(step.created_at)}
                        </span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">{step.summary}</p>
                    {step.sources && step.sources.length > 0 && (
                      <div className="mt-2 text-xs text-zinc-500">
                        Sources: {JSON.stringify(step.sources)}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
