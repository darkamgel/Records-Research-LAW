"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { SavedSearchOut, RecordOut } from "@/types";
import { RecordsTable } from "@/components/RecordsTable";

interface ExecResult {
  result_count: number;
  new_result_ids: string[];
  removed_result_ids: string[];
  items: RecordOut[];
}

export default function SavedSearchesPage() {
  const qc = useQueryClient();
  const [result, setResult] = useState<{ id: string; data: ExecResult } | null>(null);

  const { data } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => apiFetch<SavedSearchOut[]>("/saved-searches"),
  });

  const exec = useMutation({
    mutationFn: (id: string) => apiFetch<ExecResult>(`/saved-searches/${id}/execute`, { method: "POST" }),
    onSuccess: (d, id) => {
      setResult({ id, data: d });
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
    },
  });

  const del = useMutation({
    mutationFn: (id: string) => apiFetch(`/saved-searches/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-searches"] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Saved Searches</h1>
      <div className="card divide-y divide-gray-100">
        {(data || []).map((s) => (
          <div key={s.id} className="p-4 flex items-center justify-between">
            <div>
              <div className="font-medium">{s.name}</div>
              <div className="text-xs text-gray-500">
                Last run:{" "}
                {s.last_executed_at ? new Date(s.last_executed_at).toLocaleString() : "never"}
                {s.last_result_count != null && ` · ${s.last_result_count} results`}
              </div>
            </div>
            <div className="flex gap-2">
              <button className="btn-secondary" onClick={() => exec.mutate(s.id)}>
                Run
              </button>
              <button className="btn-danger" onClick={() => del.mutate(s.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {data && data.length === 0 && (
          <p className="p-4 text-gray-500">No saved searches. Save one from the Search page.</p>
        )}
      </div>

      {result && (
        <div className="card">
          <div className="p-3 border-b text-sm">
            {result.data.result_count} results ·{" "}
            <span className="text-green-700">{result.data.new_result_ids.length} new</span> ·{" "}
            <span className="text-red-700">{result.data.removed_result_ids.length} removed</span>{" "}
            since last run
          </div>
          <RecordsTable records={result.data.items} />
        </div>
      )}
    </div>
  );
}
