"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import Markdown from "react-markdown";

export default function ProblemsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProblemId, setSelectedProblemId] = useState<string | null>(null);

  const problems = useQuery({
    queryKey: ["problems"],
    queryFn: api.problems.list,
    refetchInterval: 10_000,
  });

  const allProblems = problems.data ?? [];

  // Filter problems
  const filteredProblems = useMemo(() => {
    let filtered = [...allProblems];

    if (statusFilter !== "all") {
      filtered = filtered.filter((p) => p.status === statusFilter);
    }

    if (searchQuery) {
      filtered = filtered.filter((p) =>
        p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    return filtered;
  }, [allProblems, statusFilter, searchQuery]);

  const selectedProblem = allProblems.find((p) => p.id === selectedProblemId);

  return (
    <div>
      <div className="page-header mb-8">
        <h1 className="page-title">Problems</h1>
        <p className="page-subtitle">
          View all submitted problems, their solutions, verdicts, and reasoning trails.
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search problems..."
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-acorn-500 focus:ring-2 focus:ring-acorn-500/20 focus:outline-none"
        />
        <div className="flex gap-2 overflow-x-auto">
          {["all", "active", "complete", "failed", "recovery"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                statusFilter === status
                  ? "bg-acorn-600 text-white"
                  : "bg-slate-200 text-slate-700 hover:bg-slate-300"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Problem List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-slate-900">
                Problems ({filteredProblems.length})
              </h2>
            </CardHeader>
            <CardContent>
              {filteredProblems.length === 0 ? (
                <div className="py-12 text-center">
                  <p className="text-sm text-slate-500">No problems found</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Try adjusting your filters or search query
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredProblems.map((problem) => (
                    <button
                      key={problem.id}
                      onClick={() => setSelectedProblemId(problem.id)}
                      className={`w-full text-left rounded-lg border-2 p-4 transition-all ${
                        selectedProblemId === problem.id
                          ? "border-acorn-500 bg-acorn-50"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="text-sm font-semibold text-slate-900 flex-1 line-clamp-2">
                          {problem.title}
                        </h3>
                        <StatusBadge status={problem.status} />
                      </div>
                      <p className="text-xs text-slate-600 line-clamp-2 mb-2">
                        {problem.description || "No description"}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 font-mono">
                          {problem.id.substring(0, 8)}...
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {formatDate(problem.created_at)}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Detail Panel */}
        <div className="lg:col-span-1">
          {selectedProblem ? (
            <ProblemDetailPanel problem={selectedProblem} />
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <p className="text-sm text-slate-500">
                    Select a problem to view details
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function ProblemDetailPanel({ problem }: { problem: any }) {
  const [showSolution, setShowSolution] = useState(false);
  const [showVerdict, setShowVerdict] = useState(false);
  const [showTrail, setShowTrail] = useState(false);

  const solution = useQuery({
    queryKey: ["problem-solution", problem.id],
    queryFn: async () => {
      try {
        const response = await fetch(
          api.problems.fileUrl(problem.id, "SOLUTION.md")
        );
        if (!response.ok) return null;
        return response.text();
      } catch {
        return null;
      }
    },
    enabled: showSolution,
  });

  const verdictData = useQuery({
    queryKey: ["judge-verdict", problem.id],
    queryFn: () => api.judgeVerdicts(problem.id),
    enabled: showVerdict,
  });

  const reasoningTrail = useQuery({
    queryKey: ["reasoning-trail", problem.id],
    queryFn: () => api.problems.reasoningTrail(problem.id),
    enabled: showTrail,
  });

  const files = useQuery({
    queryKey: ["problem-files", problem.id],
    queryFn: () => api.problems.files(problem.id),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900 line-clamp-2">
            {problem.title}
          </h2>
          <Badge variant="secondary" className="w-fit mt-2">
            {problem.status}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs font-medium text-slate-600 mb-1">Description</p>
            <p className="text-xs text-slate-700 line-clamp-4">
              {problem.description || "No description"}
            </p>
          </div>

          <div className="pt-2 border-t border-slate-100">
            <p className="text-[10px] text-slate-500">
              Created {formatDate(problem.created_at)}
            </p>
            {problem.updated_at && (
              <p className="text-[10px] text-slate-500">
                Updated {formatDate(problem.updated_at)}
              </p>
            )}
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-100">
            <button
              onClick={() => setShowSolution(!showSolution)}
              className="w-full rounded-lg bg-slate-100 hover:bg-slate-200 px-3 py-2 text-xs font-medium text-slate-900 transition-colors text-left flex items-center justify-between"
            >
              SOLUTION.md
              <span>{showSolution ? "▼" : "▶"}</span>
            </button>

            {showSolution && solution.data && (
              <div className="rounded-lg bg-slate-50 p-3 max-h-64 overflow-y-auto border border-slate-200">
                <div className="prose prose-sm text-xs">
                  <Markdown>{solution.data}</Markdown>
                </div>
              </div>
            )}

            <button
              onClick={() => setShowVerdict(!showVerdict)}
              className="w-full rounded-lg bg-slate-100 hover:bg-slate-200 px-3 py-2 text-xs font-medium text-slate-900 transition-colors text-left flex items-center justify-between"
            >
              Judge Verdict
              <span>{showVerdict ? "▼" : "▶"}</span>
            </button>

            {showVerdict && verdictData.data && verdictData.data.length > 0 && (
              <div className="rounded-lg bg-slate-50 p-3 max-h-64 overflow-y-auto border border-slate-200 space-y-2">
                {verdictData.data.map((verdict) => (
                  <div key={verdict.id} className="p-2 bg-white rounded border border-slate-200">
                    <p className="text-xs font-semibold mb-1 text-slate-900">
                      {verdict.verdict}
                    </p>
                    {typeof verdict.checks === "object" &&
                      verdict.checks &&
                      Object.entries(verdict.checks).map(([key, value]) => (
                        <div key={key} className="flex items-center gap-2 text-[10px]">
                          <span className={value ? "text-green-600" : "text-red-600"}>
                            {value ? "✓" : "✗"}
                          </span>
                          <span className="text-slate-600">{key}</span>
                        </div>
                      ))}
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => setShowTrail(!showTrail)}
              className="w-full rounded-lg bg-slate-100 hover:bg-slate-200 px-3 py-2 text-xs font-medium text-slate-900 transition-colors text-left flex items-center justify-between"
            >
              Reasoning Trail
              <span>{showTrail ? "▼" : "▶"}</span>
            </button>

            {showTrail && reasoningTrail.data && (
              <div className="rounded-lg bg-slate-50 p-3 max-h-64 overflow-y-auto border border-slate-200 space-y-1">
                {reasoningTrail.data.steps.map((step, idx) => (
                  <div key={idx} className="text-[10px] p-1.5 bg-white rounded border border-slate-100">
                    <div className="font-semibold text-slate-900 mb-0.5">
                      {step.step_type}
                    </div>
                    <p className="text-slate-700 line-clamp-2">{step.summary}</p>
                    {step.confidence !== null && (
                      <span className="text-slate-500">
                        {(step.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {files.data && files.data.files.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-600 mb-2">Files</p>
              <div className="space-y-1">
                {files.data.files.slice(0, 5).map((file) => (
                  <a
                    key={file.name}
                    href={api.problems.fileUrl(problem.id, file.name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-acorn-600 hover:text-acorn-700 block truncate font-mono"
                  >
                    {file.name}
                  </a>
                ))}
                {files.data.files.length > 5 && (
                  <p className="text-[10px] text-slate-400">
                    +{files.data.files.length - 5} more
                  </p>
                )}
              </div>
            </div>
          )}

          {problem.status === "failed" && (
            <Button
              className="w-full bg-amber-600 hover:bg-amber-700 text-white text-xs"
              onClick={() => {
                // This would normally spawn a recovery problem
                alert("Recovery problem spawn not yet implemented");
              }}
            >
              Spawn Recovery
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
