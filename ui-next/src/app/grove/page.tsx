"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

const domainColors: Record<string, string> = {
  "data-engineering": "bg-blue-100 text-blue-700",
  "data-science": "bg-purple-100 text-purple-700",
  "etl": "bg-cyan-100 text-cyan-700",
  "ml": "bg-pink-100 text-pink-700",
  "ui": "bg-green-100 text-green-700",
  "infra": "bg-gray-100 text-gray-700",
  "analysis": "bg-amber-100 text-amber-700",
  "feature-engineering": "bg-indigo-100 text-indigo-700",
  "model-training": "bg-red-100 text-red-700",
  "visualization": "bg-teal-100 text-teal-700",
};

const domainHexagons = [
  "data-engineering",
  "data-science",
  "etl",
  "ml",
  "ui",
  "infra",
  "analysis",
  "feature-engineering",
  "model-training",
  "visualization",
];

export default function GrovePage() {
  const queryClient = useQueryClient();
  const [filterDomain, setFilterDomain] = useState<string | null>(null);

  const kernels = useQuery({
    queryKey: ["kernels"],
    queryFn: () => api.kernels.list(),
    refetchInterval: 10_000,
  });

  const promoteMutation = useMutation({
    mutationFn: api.kernels.promote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kernels"] });
    },
  });

  const promoteAllMutation = useMutation({
    mutationFn: async () => {
      // Call the auto-promote endpoint (needs to be added to API)
      const response = await fetch("/acorn-api/api/kernels/auto-promote", {
        method: "POST",
      });
      if (!response.ok) throw new Error("Auto-promote failed");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kernels"] });
    },
  });

  const allKernels = kernels.data ?? [];
  const filteredKernels = filterDomain
    ? allKernels.filter((k) => k.category === filterDomain)
    : allKernels;

  const permanentKernels = allKernels.filter((k) => k.status === "permanent");
  const probationaryKernels = allKernels.filter(
    (k) => k.status === "probationary"
  );
  const promoteableKernels = probationaryKernels.filter(
    (k) => (k.verified_on_problems ?? []).length >= 1
  );

  const domainCounts: Record<string, number> = {};
  domainHexagons.forEach((d) => {
    domainCounts[d] = permanentKernels.filter((k) => k.category === d).length;
  });

  const canPromote = (kernel: any): boolean => {
    return kernel.status === "probationary";
  };

  return (
    <div>
      <div className="page-header mb-8">
        <h1 className="page-title">Kernel Grove</h1>
        <p className="page-subtitle">
          Living kernel library showing the promotion pipeline from probationary
          to permanent kernels.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <MetricCard
          label="Total Kernels"
          value={allKernels.length}
          subtext={`${permanentKernels.length} permanent`}
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
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          }
        />
        <MetricCard
          label="Permanent"
          value={permanentKernels.length}
          subtext="Production-ready"
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
                d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
              />
            </svg>
          }
        />
        <MetricCard
          label="Probationary"
          value={probationaryKernels.length}
          subtext={`${promoteableKernels.length} ready`}
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
                d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <MetricCard
          label="Total Uses"
          value={allKernels.reduce((sum, k) => sum + k.use_count, 0)}
          subtext="Cross-problem reuse"
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
                d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
              />
            </svg>
          }
        />
      </div>

      {/* Domain Coverage Map */}
      <Card className="mb-8">
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-900">
            Domain Coverage Map
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Color intensity shows permanent kernel count per domain
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {domainHexagons.map((domain) => {
              const count = domainCounts[domain] ?? 0;
              const maxCount = Math.max(...Object.values(domainCounts), 5);
              const intensity = (count / maxCount) * 100;
              const isGapped = count === 0;

              return (
                <button
                  key={domain}
                  onClick={() =>
                    setFilterDomain(filterDomain === domain ? null : domain)
                  }
                  className={`aspect-square rounded-lg p-3 text-center transition-all cursor-pointer border-2 ${
                    filterDomain === domain
                      ? "border-acorn-500 ring-2 ring-acorn-400"
                      : "border-slate-200 hover:border-slate-300"
                  } ${
                    isGapped
                      ? "bg-amber-50 hover:bg-amber-100"
                      : `bg-gradient-to-br from-acorn-50 to-acorn-100`
                  }`}
                >
                  <div className="flex flex-col items-center justify-center h-full gap-1">
                    <div className="text-2xl font-bold text-slate-900">
                      {count}
                    </div>
                    <div className="text-[10px] font-medium text-slate-600 uppercase tracking-wider">
                      {domain.replace(/-/g, " ")}
                    </div>
                    {isGapped && (
                      <div className="text-xs text-amber-600 font-semibold">
                        Gap
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Action button */}
      <div className="mb-8 flex gap-3">
        <Button
          onClick={() => promoteAllMutation.mutate()}
          loading={promoteAllMutation.isPending}
          className="bg-acorn-600 text-white hover:bg-acorn-700"
        >
          Auto-Promote Ready Kernels
        </Button>
        <span className="text-sm text-slate-500 flex items-center">
          {promoteableKernels.length} kernel{promoteableKernels.length !== 1 ? "s" : ""} ready for promotion
        </span>
      </div>

      {/* Kanban Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Probationary Column */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-amber-500" />
            Probationary ({probationaryKernels.length})
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {probationaryKernels.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                No probationary kernels
              </p>
            ) : (
              probationaryKernels.map((kernel) => (
                <KernelCard
                  key={kernel.id}
                  kernel={kernel}
                  onPromote={() => promoteMutation.mutate(kernel.id)}
                  promoting={promoteMutation.isPending}
                  showPromoteBtn={canPromote(kernel)}
                />
              ))
            )}
          </div>
        </div>

        {/* Promotion Candidates Column */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-blue-500" />
            Ready for Promotion ({promoteableKernels.length})
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {promoteableKernels.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                No kernels verified yet
              </p>
            ) : (
              promoteableKernels.map((kernel) => (
                <KernelCard
                  key={kernel.id}
                  kernel={kernel}
                  onPromote={() => promoteMutation.mutate(kernel.id)}
                  promoting={promoteMutation.isPending}
                  showPromoteBtn={true}
                  highlighted={true}
                />
              ))
            )}
          </div>
        </div>

        {/* Permanent Column */}
        <div className="bg-white rounded-lg border border-gold-200 bg-gradient-to-b from-yellow-50 to-white p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <span className="text-lg">★</span>
            Permanent ({permanentKernels.length})
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {permanentKernels.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                No permanent kernels yet
              </p>
            ) : (
              permanentKernels.map((kernel) => (
                <KernelCard
                  key={kernel.id}
                  kernel={kernel}
                  permanent={true}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Filtered view if domain selected */}
      {filterDomain && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-900">
              {filterDomain} Kernels ({filteredKernels.length})
            </h2>
            <button
              onClick={() => setFilterDomain(null)}
              className="text-xs text-acorn-600 hover:text-acorn-700 mt-2"
            >
              Clear filter
            </button>
          </CardHeader>
          <CardContent>
            {filteredKernels.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">
                No kernels in this domain
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredKernels.map((kernel) => (
                  <div key={kernel.id} className="border border-slate-200 rounded-lg p-3">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="text-sm font-semibold text-slate-900 flex-1">
                        {kernel.name}
                      </h4>
                      {kernel.status === "permanent" && (
                        <span className="text-lg">★</span>
                      )}
                    </div>
                    <Badge variant="secondary" className="text-xs mb-2">
                      {kernel.category}
                    </Badge>
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
                      <span>{kernel.use_count} uses</span>
                      <span className="font-mono">
                        {(kernel.verified_on_problems ?? []).length}/2
                      </span>
                    </div>
                    {kernel.trigger_keywords && (
                      <div className="flex flex-wrap gap-1">
                        {kernel.trigger_keywords.slice(0, 3).map((kw: string) => (
                          <span
                            key={kw}
                            className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function KernelCard({
  kernel,
  onPromote,
  promoting,
  showPromoteBtn = false,
  permanent = false,
  highlighted = false,
}: {
  kernel: any;
  onPromote?: () => void;
  promoting?: boolean;
  showPromoteBtn?: boolean;
  permanent?: boolean;
  highlighted?: boolean;
}) {
  const verifiedCount = (kernel.verified_on_problems ?? []).length;

  return (
    <div
      className={`rounded-lg p-3 border-2 transition-all ${
        permanent
          ? "border-yellow-300 bg-yellow-50"
          : highlighted
            ? "border-blue-300 bg-blue-50"
            : "border-slate-200 bg-white hover:border-slate-300"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-xs font-semibold text-slate-900 truncate">
            {kernel.name}
          </h4>
          <p className="text-[10px] text-slate-500 mt-0.5 truncate">
            {kernel.description}
          </p>
        </div>
        {permanent && <span className="text-sm">★</span>}
      </div>

      <div className="flex items-center gap-2 mb-2">
        <Badge variant="secondary" className="text-[10px]">
          {kernel.category}
        </Badge>
        <span className="text-[10px] text-slate-500">{kernel.use_count}x</span>
      </div>

      {kernel.status === "probationary" && (
        <div className="mb-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-slate-500">Verifications</span>
            <span className="text-[10px] font-mono text-slate-700">
              {verifiedCount}/2
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-slate-200 overflow-hidden">
            <div
              className={`h-full transition-all ${
                verifiedCount >= 2
                  ? "bg-green-500"
                  : verifiedCount >= 1
                    ? "bg-blue-500"
                    : "bg-amber-500"
              }`}
              style={{ width: `${Math.min(100, (verifiedCount / 2) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {showPromoteBtn && (
        <Button
          onClick={onPromote}
          loading={promoting}
          size="sm"
          variant="secondary"
          className="w-full text-xs"
        >
          Promote
        </Button>
      )}
    </div>
  );
}

// Helper for cn
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
