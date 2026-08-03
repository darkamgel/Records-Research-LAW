"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface AIStatus {
  configured: boolean;
  model: string;
  source: string;
  base_url: string;
}

interface Msg {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "Hi — I’m a simple LLM test bot. Ask me anything short to verify your API key, base URL, and model are working.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: status } = useQuery({
    queryKey: ["ai-settings"],
    queryFn: () => apiFetch<AIStatus>("/settings/ai"),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setError(null);
    setInput("");
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setBusy(true);
    try {
      const history = next
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(0, -1) // exclude the message we just added; API appends it
        .slice(-16);
      const res = await apiFetch<{ reply: string; model: string }>("/settings/ai/chat", {
        method: "POST",
        body: { message: text, history },
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">LLM chat (test bot)</h1>
          <p className="text-sm text-gray-500 mt-1">
            Talk to your configured model to confirm the connection works before using AI reports.
          </p>
        </div>
        <Link href="/settings" className="btn-secondary">
          AI settings
        </Link>
      </div>

      <div className="card p-3 text-sm flex flex-wrap gap-x-4 gap-y-1">
        <span>
          Status:{" "}
          <strong className={status?.configured ? "text-green-700" : "text-amber-700"}>
            {status?.configured ? "configured" : "not configured"}
          </strong>
        </span>
        <span className="text-gray-500">Model: {status?.model || "—"}</span>
        <span className="text-gray-500">Source: {status?.source || "—"}</span>
      </div>

      {!status?.configured && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          No API key yet. Open{" "}
          <Link href="/settings" className="underline font-medium">
            Settings → AI / LLM
          </Link>{" "}
          and paste your key (and base URL if you use a custom OpenAI-compatible server).
        </div>
      )}

      <div className="card flex flex-col h-[min(70vh,560px)]">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {busy && (
            <div className="text-xs text-gray-400">Thinking…</div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && (
          <div className="px-4 pb-2 text-sm text-red-600 border-t border-gray-100 pt-2">{error}</div>
        )}

        <form
          className="border-t border-gray-200 p-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <input
            className="input"
            placeholder={status?.configured ? "Ask something…" : "Configure AI in Settings first"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy || !status?.configured}
            aria-label="chat message"
          />
          <button className="btn-primary shrink-0" type="submit" disabled={busy || !status?.configured}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
