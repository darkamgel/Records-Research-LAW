"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Page, RecordOut } from "@/types";
import { RecordsTable } from "@/components/RecordsTable";

interface Query {
  q?: string;
  mode: string;
  name?: string;
  address?: string;
  case_number?: string;
  jurisdiction?: string;
  record_type?: string;
  state?: string;
  filing_date_from?: string;
  filing_date_to?: string;
  limit: number;
  offset: number;
}

const MODES = [
  ["keyword", "Keyword"],
  ["fulltext", "Full-text"],
  ["semantic", "Semantic"],
  ["fuzzy_name", "Fuzzy name"],
  ["exact_name", "Exact name"],
];

export default function SearchPage() {
  const [query, setQuery] = useState<Query>({ mode: "keyword", limit: 25, offset: 0 });
  const [saveName, setSaveName] = useState("");
  const [saved, setSaved] = useState(false);

  const search = useMutation({
    mutationFn: (q: Query) =>
      apiFetch<Page<RecordOut>>("/records/search", { method: "POST", body: q }),
  });

  function update<K extends keyof Query>(k: K, v: Query[K]) {
    setQuery((prev) => ({ ...prev, [k]: v }));
  }

  function run(offset = 0) {
    const q = { ...query, offset };
    setQuery(q);
    search.mutate(q);
  }

  async function saveSearch() {
    if (!saveName) return;
    await apiFetch("/saved-searches", {
      method: "POST",
      body: { name: saveName, query },
    });
    setSaved(true);
    setSaveName("");
    setTimeout(() => setSaved(false), 2000);
  }

  const data = search.data;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Search</h1>
      <div className="card p-4 space-y-3">
        <div className="grid md:grid-cols-3 gap-3">
          <div className="md:col-span-2">
            <label className="label">Query</label>
            <input
              className="input"
              placeholder="keyword, phrase, or semantic query"
              value={query.q || ""}
              onChange={(e) => update("q", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Mode</label>
            <select
              className="input"
              value={query.mode}
              onChange={(e) => update("mode", e.target.value)}
            >
              {MODES.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid md:grid-cols-4 gap-3">
          <div>
            <label className="label">Name</label>
            <input className="input" value={query.name || ""} onChange={(e) => update("name", e.target.value)} />
          </div>
          <div>
            <label className="label">Address</label>
            <input className="input" value={query.address || ""} onChange={(e) => update("address", e.target.value)} />
          </div>
          <div>
            <label className="label">Case #</label>
            <input className="input" value={query.case_number || ""} onChange={(e) => update("case_number", e.target.value)} />
          </div>
          <div>
            <label className="label">Jurisdiction</label>
            <input className="input" value={query.jurisdiction || ""} onChange={(e) => update("jurisdiction", e.target.value)} />
          </div>
          <div>
            <label className="label">Record type</label>
            <input className="input" value={query.record_type || ""} onChange={(e) => update("record_type", e.target.value)} />
          </div>
          <div>
            <label className="label">State</label>
            <input className="input" value={query.state || ""} onChange={(e) => update("state", e.target.value)} />
          </div>
          <div>
            <label className="label">Filed from</label>
            <input className="input" type="date" value={query.filing_date_from || ""} onChange={(e) => update("filing_date_from", e.target.value)} />
          </div>
          <div>
            <label className="label">Filed to</label>
            <input className="input" type="date" value={query.filing_date_to || ""} onChange={(e) => update("filing_date_to", e.target.value)} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-primary" onClick={() => run(0)} disabled={search.isPending}>
            {search.isPending ? "Searching…" : "Search"}
          </button>
          <input
            className="input max-w-[200px]"
            placeholder="Save search as…"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
          />
          <button className="btn-secondary" onClick={saveSearch} disabled={!saveName}>
            {saved ? "Saved!" : "Save search"}
          </button>
        </div>
      </div>

      {data && (
        <div className="card">
          <div className="p-3 border-b text-sm text-gray-600">
            {data.total} result(s)
          </div>
          <RecordsTable records={data.items} />
          {data.total > data.limit && (
            <div className="p-3 flex justify-between text-sm">
              <button
                className="btn-secondary"
                disabled={query.offset === 0}
                onClick={() => run(Math.max(0, query.offset - query.limit))}
              >
                Previous
              </button>
              <span className="text-gray-500">
                Showing {query.offset + 1}–{Math.min(query.offset + data.limit, data.total)}
              </span>
              <button
                className="btn-secondary"
                disabled={query.offset + query.limit >= data.total}
                onClick={() => run(query.offset + query.limit)}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
