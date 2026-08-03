"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch, API_URL, getToken, getWorkspace } from "@/lib/api";
import type { Page, RecordOut } from "@/types";
import { RecordsTable } from "@/components/RecordsTable";

export default function RecordsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["records", "all"],
    queryFn: () =>
      apiFetch<Page<RecordOut>>("/records/search", {
        method: "POST",
        body: { limit: 100, offset: 0, sort: "created_at", sort_dir: "desc" },
      }),
  });

  function exportCsv() {
    // Direct navigation with headers is not possible; use fetch + blob.
    fetch(`${API_URL}/records/export`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
        "X-Workspace-Id": getWorkspace() || "",
      },
      body: JSON.stringify({ limit: 5000 }),
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "records.csv";
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Records</h1>
        <button className="btn-secondary" onClick={exportCsv}>
          Export CSV
        </button>
      </div>
      <div className="card">
        {isLoading || !data ? (
          <p className="p-4 text-gray-500">Loading…</p>
        ) : (
          <>
            <div className="p-3 border-b text-sm text-gray-600">{data.total} record(s)</div>
            <RecordsTable records={data.items} />
          </>
        )}
      </div>
    </div>
  );
}
