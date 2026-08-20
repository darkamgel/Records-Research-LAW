"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, API_URL, getToken, getWorkspace } from "@/lib/api";
import type { AdapterDescriptor } from "@/types";

const FR_DOC_TYPES = [
  { value: "NOTICE", label: "Notices" },
  { value: "RULE", label: "Final rules" },
  { value: "PROPOSED RULE", label: "Proposed rules" },
  { value: "", label: "All document types" },
] as const;

export default function ImportPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [prov, setProv] = useState({ source_name: "", original_url: "", jurisdiction: "", record_type: "" });
  const [frDocType, setFrDocType] = useState("NOTICE");
  const [frLimit, setFrLimit] = useState(50);

  const { data: adapters } = useQuery({
    queryKey: ["adapters"],
    queryFn: () => apiFetch<AdapterDescriptor[]>("/sources/adapters"),
  });

  const importDemo = useMutation({
    mutationFn: async () => {
      const src = await apiFetch<{ id: string }>("/sources", {
        method: "POST",
        body: {
          source_key: "demo",
          source_name: "Demonstration Public Records (Synthetic)",
          source_type: "demo",
          access_method: "sample_data",
        },
      });
      return apiFetch<{ records_created: number }>(`/sources/${src.id}/import`, {
        method: "POST",
        body: { limit: 50 },
      });
    },
    onSuccess: (res) => {
      setMsg(`Imported ${res.records_created} demonstration records.`);
      qc.invalidateQueries();
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Import failed"),
  });

  const importFederalRegister = useMutation({
    mutationFn: async () => {
      const limit = Math.min(Math.max(frLimit, 1), 100);
      const config: Record<string, string> = { order: "newest" };
      if (frDocType) config.document_type = frDocType;

      const src = await apiFetch<{ id: string }>("/sources", {
        method: "POST",
        body: {
          source_key: "federal_register",
          source_name: "Federal Register (Official API)",
          source_type: "json_api",
          access_method: "official_api",
          jurisdiction: "United States",
          base_url: "https://www.federalregister.gov/api/v1",
          supported_record_types: ["public_notice", "regulatory_rule"],
          terms_notes:
            "Official Federal Register API; no API key required. Use polite request rates.",
          attribution: "Data courtesy of the U.S. Federal Register / National Archives.",
          requires_auth: false,
          rate_limit_per_minute: 30,
          config,
        },
      });
      return apiFetch<{ records_created: number; stats?: { records_skipped?: number } }>(
        `/sources/${src.id}/import`,
        { method: "POST", body: { limit, config } }
      );
    },
    onSuccess: (res) => {
      const skipped = res.stats?.records_skipped ?? 0;
      const parts = [`Imported ${res.records_created} Federal Register record(s).`];
      if (skipped > 0) parts.push(`${skipped} duplicate(s) skipped.`);
      setMsg(parts.join(" "));
      qc.invalidateQueries();
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Federal Register import failed"),
  });

  async function uploadFile() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    if (prov.source_name) fd.append("source_name", prov.source_name);
    if (prov.original_url) fd.append("original_url", prov.original_url);
    if (prov.jurisdiction) fd.append("jurisdiction", prov.jurisdiction);
    if (prov.record_type) fd.append("record_type", prov.record_type);
    const res = await fetch(`${API_URL}/files/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "X-Workspace-Id": getWorkspace() || "",
      },
      body: fd,
    });
    if (res.ok) {
      setMsg("File uploaded and processed.");
      if (fileRef.current) fileRef.current.value = "";
      qc.invalidateQueries();
    } else {
      const d = await res.json().catch(() => ({}));
      setMsg(`Upload failed: ${d.detail || res.statusText}`);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Import Data</h1>
      {msg && <div className="card p-3 text-sm bg-brand-50 border-brand-100">{msg}</div>}

      <div className="card p-4">
        <h2 className="font-medium mb-2">Demonstration data</h2>
        <p className="text-sm text-gray-500 mb-3">
          Load clearly-labeled synthetic records to explore the platform.
        </p>
        <button className="btn-primary" onClick={() => importDemo.mutate()} disabled={importDemo.isPending}>
          {importDemo.isPending ? "Importing…" : "Import demo records"}
        </button>
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-2">Federal Register (live)</h2>
        <p className="text-sm text-gray-500 mb-3">
          Pull the latest U.S. Federal Register documents via the official free API — no API key
          required. Duplicates (same document number) are skipped automatically.
        </p>
        <div className="grid md:grid-cols-3 gap-3 mb-3">
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">Document type</span>
            <select
              className="input w-full"
              value={frDocType}
              onChange={(e) => setFrDocType(e.target.value)}
            >
              {FR_DOC_TYPES.map((t) => (
                <option key={t.value || "all"} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">How many records</span>
            <input
              className="input w-full"
              type="number"
              min={1}
              max={100}
              value={frLimit}
              onChange={(e) => setFrLimit(Number(e.target.value) || 50)}
            />
          </label>
        </div>
        <button
          className="btn-primary"
          onClick={() => importFederalRegister.mutate()}
          disabled={importFederalRegister.isPending}
        >
          {importFederalRegister.isPending ? "Importing…" : "Import from Federal Register"}
        </button>
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-2">Upload a file (PDF, CSV, TXT, JSON)</h2>
        <div className="grid md:grid-cols-4 gap-3 mb-3">
          <input className="input" placeholder="Source name" value={prov.source_name} onChange={(e) => setProv({ ...prov, source_name: e.target.value })} />
          <input className="input" placeholder="Original URL" value={prov.original_url} onChange={(e) => setProv({ ...prov, original_url: e.target.value })} />
          <input className="input" placeholder="Jurisdiction" value={prov.jurisdiction} onChange={(e) => setProv({ ...prov, jurisdiction: e.target.value })} />
          <input className="input" placeholder="Record type" value={prov.record_type} onChange={(e) => setProv({ ...prov, record_type: e.target.value })} />
        </div>
        <input ref={fileRef} type="file" accept=".pdf,.csv,.txt,.json" className="mb-3 block text-sm" />
        <button className="btn-primary" onClick={uploadFile}>
          Upload &amp; process
        </button>
        <p className="text-xs text-gray-500 mt-2">
          Files are validated by type and size; duplicates are detected by SHA-256.
        </p>
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-3">Available source adapters</h2>
        <div className="space-y-3">
          {(adapters || []).map((a) => (
            <div key={a.source_key} className="border border-gray-100 rounded-md p-3 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{a.source_name}</span>
                <span className="badge bg-gray-100 text-gray-600">{a.access_method}</span>
              </div>
              <p className="text-gray-600 mt-1">{a.terms_notes}</p>
              <p className="text-xs text-gray-400 mt-1">
                Attribution: {a.attribution} · Requires auth: {a.requires_auth ? "yes" : "no"}
                {a.rate_limit_per_minute ? ` · ${a.rate_limit_per_minute}/min` : ""}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
