"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { DashboardMetrics } from "@/types";

function Metric({ label, value, href }: { label: string; value: number; href?: string }) {
  const body = (
    <div className="card p-4">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<DashboardMetrics>("/dashboard/metrics"),
  });

  if (isLoading || !data) return <div className="text-gray-500">Loading metrics…</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <Link href="/guide" className="btn-secondary">
          How to use this app
        </Link>
      </div>

      <div className="rounded-md border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-900 flex flex-wrap items-center justify-between gap-3">
        <span>
          New here? Follow the in-app guide: import data → search → review matches → build a report.
        </span>
        <Link href="/guide" className="font-medium underline underline-offset-2 shrink-0">
          Open user guide
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Total records" value={data.total_records} href="/records" />
        <Metric label="Total documents" value={data.total_documents} href="/documents" />
        <Metric label="Records this week" value={data.records_this_week} />
        <Metric label="Documents pending" value={data.documents_pending} href="/jobs" />
        <Metric
          label="Matches to review"
          value={data.matches_pending_review}
          href="/matches"
        />
        <Metric label="Matches reviewed" value={data.matches_reviewed} href="/matches" />
        <Metric label="Failed jobs" value={data.failed_jobs} href="/jobs" />
      </div>

      <div className="card p-4">
        <h2 className="font-medium mb-3">Recent research activity</h2>
        {data.recent_activity.length === 0 ? (
          <p className="text-sm text-gray-500">No activity yet. Try importing demo data.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {data.recent_activity.map((a, i) => (
              <li key={i} className="py-2 text-sm flex justify-between">
                <span>
                  <span className="font-medium">{a.action}</span>
                  {a.result_count != null && (
                    <span className="text-gray-500"> · {a.result_count} results</span>
                  )}
                </span>
                <span className="text-gray-400">
                  {new Date(a.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
