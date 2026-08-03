"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { MatchCandidate } from "@/types";
import { ConfidenceBadge, ReviewBadge } from "@/components/ConfidenceBadge";

export default function MatchesPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<MatchCandidate | null>(null);

  const { data: candidates } = useQuery({
    queryKey: ["matches"],
    queryFn: () => apiFetch<MatchCandidate[]>("/matches?limit=100"),
  });

  const generate = useMutation({
    mutationFn: () =>
      apiFetch<MatchCandidate[]>("/matches/generate", {
        method: "POST",
        body: { limit: 500, use_ai_explanation: false },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["matches"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Potential Matches</h1>
        <button className="btn-primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
          {generate.isPending ? "Generating…" : "Generate candidates"}
        </button>
      </div>
      <p className="text-sm text-gray-500">
        Confidence scores are explainable review guidance, not identity confirmations.
        Every candidate must be reviewed by a person.
      </p>

      <div className="card">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="p-2">Confidence</th>
              <th className="p-2">Status</th>
              <th className="p-2">Rationale</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {(candidates || []).map((c) => (
              <tr key={c.id} className="border-b border-gray-100">
                <td className="p-2">
                  <ConfidenceBadge score={c.confidence_score} category={c.category} />
                </td>
                <td className="p-2">
                  <ReviewBadge status={c.review_status} />
                </td>
                <td className="p-2 text-gray-600 max-w-md truncate">{c.rationale}</td>
                <td className="p-2 text-right">
                  <button className="btn-secondary" onClick={() => setSelected(c)}>
                    Review
                  </button>
                </td>
              </tr>
            ))}
            {candidates && candidates.length === 0 && (
              <tr>
                <td className="p-4 text-gray-500" colSpan={4}>
                  No candidates yet. Click “Generate candidates”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <ReviewModal candidateId={selected.id} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function ReviewModal({ candidateId, onClose }: { candidateId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");
  const { data: c } = useQuery({
    queryKey: ["match", candidateId],
    queryFn: () => apiFetch<MatchCandidate>(`/matches/${candidateId}`),
  });

  const review = useMutation({
    mutationFn: (decision: string) =>
      apiFetch(`/matches/${candidateId}/review`, {
        method: "POST",
        body: { decision, notes },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matches"] });
      onClose();
    },
  });

  if (!c) return null;
  const a = c.record_a;
  const b = c.record_b;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Review potential match</h2>
          <ConfidenceBadge score={c.confidence_score} category={c.category} />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          {[a, b].map((r, i) => (
            <div key={i} className="card p-3 text-sm space-y-1">
              <div className="font-medium">{r?.title || r?.primary_name}</div>
              <Field k="Name" v={r?.primary_name} />
              <Field k="Case #" v={r?.case_number} />
              <Field k="Filed" v={r?.filing_date} />
              <Field k="Address" v={r?.normalized_address} />
              <Field k="Jurisdiction" v={r?.jurisdiction} />
              {r?.original_url && (
                <a href={r.original_url} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline text-xs">
                  Open source
                </a>
              )}
            </div>
          ))}
        </div>

        <div className="mb-3">
          <h3 className="font-medium text-sm mb-1">Rationale</h3>
          <p className="text-sm text-gray-600">{c.rationale}</p>
          {c.rationale_source === "ai" && (
            <span className="badge bg-purple-100 text-purple-800 mt-1">AI-assisted explanation</span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
          <div>
            <h3 className="font-medium mb-1 text-green-700">Supporting</h3>
            <ul className="list-disc pl-5 text-gray-600">
              {(c.supporting_evidence || []).map((e, i) => (
                <li key={i}>{String((e as { detail?: string }).detail)}</li>
              ))}
              {(!c.supporting_evidence || c.supporting_evidence.length === 0) && <li>None</li>}
            </ul>
          </div>
          <div>
            <h3 className="font-medium mb-1 text-red-700">Conflicting</h3>
            <ul className="list-disc pl-5 text-gray-600">
              {(c.conflicting_evidence || []).map((e, i) => (
                <li key={i}>{String((e as { detail?: string }).detail)}</li>
              ))}
              {(!c.conflicting_evidence || c.conflicting_evidence.length === 0) && <li>None</li>}
            </ul>
          </div>
        </div>

        {c.missing_information && c.missing_information.length > 0 && (
          <p className="text-xs text-gray-500 mb-3">
            Missing information: {c.missing_information.join(", ")}
          </p>
        )}

        <textarea
          className="input mb-3"
          rows={2}
          placeholder="Reviewer notes…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />

        <div className="flex flex-wrap gap-2 justify-end">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-secondary" onClick={() => review.mutate("needs_more_info")}>
            Needs more info
          </button>
          <button className="btn-secondary" onClick={() => review.mutate("duplicate")}>
            Duplicate
          </button>
          <button className="btn-danger" onClick={() => review.mutate("rejected")}>
            Reject
          </button>
          <button className="btn-primary" onClick={() => review.mutate("confirmed")}>
            Confirm for project
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{k}</span>
      <span className="text-right">{v || "-"}</span>
    </div>
  );
}
