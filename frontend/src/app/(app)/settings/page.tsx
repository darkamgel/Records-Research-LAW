"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Compliance {
  title: string;
  summary: string;
  restrictions: string[];
  ai_mode: string;
}

interface AISettings {
  enabled: boolean;
  configured: boolean;
  source: string;
  has_api_key: boolean;
  api_key_hint: string | null;
  base_url: string;
  model: string;
  embedding_model: string;
  ui_enabled: boolean;
  env_fallback_available: boolean;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<{ status: string; ai_enabled: boolean; env: string }>("/health"),
  });
  const { data: compliance } = useQuery({
    queryKey: ["compliance"],
    queryFn: () => apiFetch<Compliance>("/compliance"),
  });
  const { data: ai } = useQuery({
    queryKey: ["ai-settings"],
    queryFn: () => apiFetch<AISettings>("/settings/ai"),
  });

  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [embeddingModel, setEmbeddingModel] = useState("text-embedding-3-small");
  const [enabled, setEnabled] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (!ai) return;
    setBaseUrl(ai.base_url || "");
    setModel(ai.model || "gpt-4o-mini");
    setEmbeddingModel(ai.embedding_model || "text-embedding-3-small");
    setEnabled(ai.ui_enabled);
  }, [ai]);

  const save = useMutation({
    mutationFn: () =>
      apiFetch<AISettings>("/settings/ai", {
        method: "PUT",
        body: {
          enabled,
          api_key: apiKey.trim() || null,
          clear_api_key: false,
          base_url: baseUrl,
          model,
          embedding_model: embeddingModel,
        },
      }),
    onSuccess: () => {
      setApiKey("");
      setMsg("AI settings saved for this workspace.");
      setTestResult(null);
      qc.invalidateQueries({ queryKey: ["ai-settings"] });
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Save failed"),
  });

  const clearKey = useMutation({
    mutationFn: () =>
      apiFetch<AISettings>("/settings/ai", {
        method: "PUT",
        body: { enabled, clear_api_key: true, base_url: baseUrl, model, embedding_model: embeddingModel },
      }),
    onSuccess: () => {
      setMsg("API key cleared for this workspace.");
      qc.invalidateQueries({ queryKey: ["ai-settings"] });
    },
  });

  const test = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean; reply?: string; error?: string; model?: string }>("/settings/ai/test", {
        method: "POST",
      }),
    onSuccess: (r) => {
      setTestResult(
        r.ok
          ? `Connection OK (${r.model}). Model replied: ${r.reply || "OK"}`
          : `Connection failed: ${r.error || "unknown error"}`
      );
    },
    onError: (e) => setTestResult(e instanceof Error ? e.message : "Test failed"),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="card p-4 text-sm flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-medium">Need help using the app?</h2>
          <p className="text-gray-500 mt-0.5">
            Step-by-step guide: import, search, review matches, and run the software locally.
          </p>
        </div>
        <Link href="/guide" className="btn-primary shrink-0">
          Open user guide
        </Link>
      </div>

      <div className="card p-4 text-sm space-y-1">
        <h2 className="font-medium mb-2">Account &amp; workspace</h2>
        <Row k="User" v={user?.user.email} />
        <Row k="Role" v={user?.user.role} />
        <Row k="Workspace" v={user?.workspaces[0]?.name} />
      </div>

      <div className="card p-4 text-sm space-y-1">
        <h2 className="font-medium mb-2">System</h2>
        <Row k="Environment" v={health?.env} />
        <Row
          k="AI (workspace)"
          v={
            ai?.configured
              ? `enabled via ${ai.source}${ai.api_key_hint ? ` (…${ai.api_key_hint})` : ""}`
              : "not configured (deterministic mode)"
          }
        />
      </div>

      <div className="card p-4 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-medium">AI / LLM</h2>
            <p className="text-sm text-gray-500 mt-1 max-w-xl">
              Configure an OpenAI-compatible API from the UI (best for deployment). Keys are stored
              encrypted per workspace and never shown again — only a short hint. Leave Base URL empty
              only for official OpenAI (<code className="text-xs">sk-…</code>) keys. For
              ConfidentialMind (<code className="text-xs">cm_api_…</code>), you must set Base URL to
              the endpoint API URL from the portal (not the portal webpage).
            </p>
          </div>
          <Link href="/chat" className="btn-secondary shrink-0">
            Open test chatbot
          </Link>
        </div>

        {msg && <p className="text-sm text-brand-700 bg-brand-50 border border-brand-100 rounded-md px-3 py-2">{msg}</p>}

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enable LLM for this workspace
        </label>

        <div className="grid md:grid-cols-2 gap-3">
          <div className="md:col-span-2">
            <label className="label">API key</label>
            <input
              className="input font-mono text-sm"
              type="password"
              autoComplete="off"
              placeholder={
                ai?.has_api_key
                  ? `Saved (ends in …${ai.api_key_hint || "****"}) — paste to replace`
                  : "sk-… or cm_api_…"
              }
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <label className="label">Base URL (optional)</label>
            <input
              className="input font-mono text-sm"
              placeholder="https://your-endpoint.example/v1"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
            <p className="text-xs text-gray-400 mt-1">
              ConfidentialMind example shape:{" "}
              <code className="bg-gray-100 px-1 rounded">
                https://…/v1/api/&lt;endpoint-id&gt;
              </code>
              . Get it from the model/endpoint page → API Keys or Endpoint quickstart. Chat model
              should match the Grants Resource ID (e.g.{" "}
              <code className="bg-gray-100 px-1 rounded">mistral-medium-3-5-128b</code>).
            </p>
          </div>
          <div>
            <label className="label">Chat model</label>
            <input className="input" value={model} onChange={(e) => setModel(e.target.value)} />
          </div>
          <div>
            <label className="label">Embedding model</label>
            <input
              className="input"
              value={embeddingModel}
              onChange={(e) => setEmbeddingModel(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save AI settings"}
          </button>
          <button className="btn-secondary" onClick={() => test.mutate()} disabled={test.isPending}>
            {test.isPending ? "Testing…" : "Test connection"}
          </button>
          <button
            className="btn-danger"
            onClick={() => clearKey.mutate()}
            disabled={clearKey.isPending || !ai?.has_api_key}
          >
            Clear saved key
          </button>
        </div>

        {testResult && (
          <p
            className={`text-sm rounded-md px-3 py-2 border ${
              testResult.startsWith("Connection OK")
                ? "bg-green-50 border-green-100 text-green-800"
                : "bg-red-50 border-red-100 text-red-700"
            }`}
          >
            {testResult}
          </p>
        )}

        {ai?.env_fallback_available && ai.source === "environment" && (
          <p className="text-xs text-gray-500">
            Currently using the server environment key as a fallback. Saving a key here will prefer
            the workspace setting for reports and the chatbot.
          </p>
        )}
      </div>

      {compliance && (
        <div className="card p-4 text-sm">
          <h2 className="font-medium mb-2">{compliance.title}</h2>
          <p className="text-gray-600 mb-2">{compliance.summary}</p>
          <ul className="list-disc pl-5 text-gray-600 space-y-1">
            {compliance.restrictions.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-gray-500 shrink-0">{k}</span>
      <span className="text-right">{v || "-"}</span>
    </div>
  );
}
