"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, API_URL, getToken, getWorkspace } from "@/lib/api";
import type { Page, ProjectOut, RecordOut } from "@/types";
import { RecordsTable } from "@/components/RecordsTable";

interface Report {
  id: string;
  title: string;
  summary_markdown: string | null;
  ai_generated: boolean;
}

export default function ProjectDetailPage() {
  const { id } = useParams() as { id: string };
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<RecordOut[]>([]);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [report, setReport] = useState<Report | null>(null);

  const { data: project } = useQuery({
    queryKey: ["project", id],
    queryFn: () => apiFetch<ProjectOut>(`/projects/${id}`),
  });

  const search = useMutation({
    mutationFn: () =>
      apiFetch<Page<RecordOut>>("/records/search", { method: "POST", body: { q, limit: 25 } }),
    onSuccess: (d) => setFound(d.items),
  });

  const addRecords = useMutation({
    mutationFn: () =>
      apiFetch(`/projects/${id}/records`, {
        method: "POST",
        body: { record_ids: Array.from(sel) },
      }),
    onSuccess: () => {
      setSel(new Set());
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
  });

  const genReport = useMutation({
    mutationFn: () =>
      apiFetch<Report>(`/projects/${id}/report`, { method: "POST", body: { use_ai: true } }),
    onSuccess: (r) => setReport(r),
  });

  function toggle(rid: string) {
    setSel((prev) => {
      const n = new Set(prev);
      if (n.has(rid)) n.delete(rid);
      else n.add(rid);
      return n;
    });
  }

  function exportReport(fmt: string) {
    if (!report) return;
    fetch(`${API_URL}/projects/reports/${report.id}/export?fmt=${fmt}`, {
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "X-Workspace-Id": getWorkspace() || "",
      },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `report.${fmt === "markdown" ? "md" : fmt}`;
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  if (!project) return <div className="text-gray-500">Loading…</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{project.name}</h1>
      <p className="text-sm text-gray-500">{project.objective}</p>

      <div className="card">
        <div className="p-3 border-b font-medium text-sm">
          Records in project ({project.records?.length || 0})
        </div>
        <RecordsTable records={project.records || []} />
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-2">Add records</h2>
        <div className="flex gap-2 mb-3">
          <input className="input" placeholder="Search records…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn-secondary" onClick={() => search.mutate()}>
            Search
          </button>
          <button className="btn-primary" disabled={sel.size === 0} onClick={() => addRecords.mutate()}>
            Add {sel.size} selected
          </button>
        </div>
        <RecordsTable records={found} selectable selected={sel} onToggle={toggle} />
      </div>

      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-medium">Research summary report</h2>
          <button className="btn-primary" onClick={() => genReport.mutate()} disabled={genReport.isPending}>
            {genReport.isPending ? "Generating…" : "Generate report"}
          </button>
        </div>
        {report && (
          <>
            <div className="flex gap-2 mb-3">
              {report.ai_generated ? (
                <span className="badge bg-purple-100 text-purple-800">AI-assisted</span>
              ) : (
                <span className="badge bg-gray-100 text-gray-700">Deterministic template</span>
              )}
              {["markdown", "json", "csv", "html"].map((f) => (
                <button key={f} className="btn-secondary" onClick={() => exportReport(f)}>
                  Export {f}
                </button>
              ))}
            </div>
            <pre className="bg-gray-50 p-3 rounded text-xs whitespace-pre-wrap max-h-96 overflow-y-auto">
              {report.summary_markdown}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}
