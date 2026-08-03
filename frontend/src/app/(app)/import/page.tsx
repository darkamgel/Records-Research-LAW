"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, API_URL, getToken, getWorkspace } from "@/lib/api";
import type { AdapterDescriptor } from "@/types";

export default function ImportPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [prov, setProv] = useState({ source_name: "", original_url: "", jurisdiction: "", record_type: "" });

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
