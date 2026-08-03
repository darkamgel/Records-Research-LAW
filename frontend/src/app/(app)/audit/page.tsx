"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AuditLogOut, Page } from "@/types";

export default function AuditPage() {
  const { data } = useQuery({
    queryKey: ["audit"],
    queryFn: () => apiFetch<Page<AuditLogOut>>("/audit?limit=100"),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Audit History</h1>
      <p className="text-sm text-gray-500">
        Immutable log of imports, searches, AI operations, reviews, and report generation.
      </p>
      <div className="card">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="p-2">Action</th>
              <th className="p-2">Target</th>
              <th className="p-2">Detail</th>
              <th className="p-2">When</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((a) => (
              <tr key={a.id} className="border-b border-gray-100">
                <td className="p-2 font-medium">{a.action}</td>
                <td className="p-2 text-gray-500">
                  {a.target_type ? `${a.target_type}` : "-"}
                </td>
                <td className="p-2 text-xs text-gray-500 max-w-md truncate">
                  {a.detail ? JSON.stringify(a.detail) : "-"}
                </td>
                <td className="p-2 text-gray-400">{new Date(a.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
