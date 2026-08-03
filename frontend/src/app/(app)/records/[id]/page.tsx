"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { RecordDetail, RecordOut } from "@/types";
import { RecordsTable } from "@/components/RecordsTable";

export default function RecordDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const qc = useQueryClient();
  const [note, setNote] = useState("");

  const { data: rec } = useQuery({
    queryKey: ["record", id],
    queryFn: () => apiFetch<RecordDetail>(`/records/${id}`),
  });
  const { data: related } = useQuery({
    queryKey: ["record", id, "related"],
    queryFn: () => apiFetch<RecordOut[]>(`/records/${id}/related`),
  });

  const addNote = useMutation({
    mutationFn: () => apiFetch(`/records/${id}/notes`, { method: "PUT", body: { body: note } }),
    onSuccess: () => {
      setNote("");
      qc.invalidateQueries({ queryKey: ["record", id] });
    },
  });

  if (!rec) return <div className="text-gray-500">Loading…</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{rec.title || rec.primary_name || "Record"}</h1>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4 space-y-1 text-sm">
          <Row k="Type" v={rec.record_type} />
          <Row k="Primary name" v={rec.primary_name} />
          <Row k="Case number" v={rec.case_number} />
          <Row k="Jurisdiction" v={rec.jurisdiction} />
          <Row k="Filing date" v={rec.filing_date} />
          <Row k="Address" v={rec.normalized_address} />
          <Row k="City/State/ZIP" v={[rec.city, rec.state, rec.zip_code].filter(Boolean).join(", ")} />
          <div className="pt-2">
            {rec.original_url ? (
              <a href={rec.original_url} target="_blank" rel="noreferrer" className="btn-secondary">
                Open original source
              </a>
            ) : (
              <span className="text-gray-400">No source URL</span>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="font-medium mb-2">Extracted entities ({rec.entities.length})</h2>
          <div className="max-h-72 overflow-y-auto text-sm space-y-1">
            {rec.entities.map((e) => (
              <div key={e.id} className="flex justify-between border-b border-gray-100 py-1">
                <span>
                  <span className="badge bg-gray-100 text-gray-700 mr-2">{e.entity_type}</span>
                  {e.value}
                </span>
                <span className="text-xs text-gray-400">
                  {e.extraction_method} · {(e.confidence * 100).toFixed(0)}%
                  {e.page_number ? ` · p.${e.page_number}` : ""}
                </span>
              </div>
            ))}
            {rec.entities.length === 0 && <p className="text-gray-500">None extracted.</p>}
          </div>
        </div>
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-2">Potentially related records</h2>
        <p className="text-xs text-gray-500 mb-2">
          Suggestions only — require human review. Not identity confirmations.
        </p>
        <RecordsTable records={related || []} />
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-2">Add note</h2>
        <textarea
          className="input"
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Reviewer note…"
        />
        <button
          className="btn-primary mt-2"
          disabled={!note || addNote.isPending}
          onClick={() => addNote.mutate()}
        >
          Save note
        </button>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{k}</span>
      <span className="text-right">{v || "-"}</span>
    </div>
  );
}
