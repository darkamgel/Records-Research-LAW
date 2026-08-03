"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface Job {
  id: string;
  job_type: string;
  status: string;
  records_created: number;
  records_failed: number;
  progress: number;
  error_message: string | null;
  created_at: string;
}
interface Upload {
  id: string;
  original_filename: string;
  mime_type: string;
  processing_status: string;
  processing_error: string | null;
  retry_count: number;
}

export default function JobsPage() {
  const qc = useQueryClient();
  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<Job[]>("/files/jobs"),
  });
  const { data: uploads } = useQuery({
    queryKey: ["uploads"],
    queryFn: () => apiFetch<Upload[]>("/files"),
  });
  const retry = useMutation({
    mutationFn: (id: string) => apiFetch(`/files/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Processing Jobs</h1>

      <div className="card">
        <div className="p-3 border-b font-medium text-sm">Ingestion jobs</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="p-2">Type</th>
              <th className="p-2">Status</th>
              <th className="p-2">Created</th>
              <th className="p-2">Failed</th>
              <th className="p-2">When</th>
            </tr>
          </thead>
          <tbody>
            {(jobs || []).map((j) => (
              <tr key={j.id} className="border-b border-gray-100">
                <td className="p-2">{j.job_type}</td>
                <td className="p-2">
                  <span
                    className={`badge ${
                      j.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : j.status === "failed"
                        ? "bg-red-100 text-red-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {j.status}
                  </span>
                  {j.error_message && (
                    <span className="text-xs text-red-600 ml-2">{j.error_message}</span>
                  )}
                </td>
                <td className="p-2">{j.records_created}</td>
                <td className="p-2">{j.records_failed}</td>
                <td className="p-2 text-gray-400">{new Date(j.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="p-3 border-b font-medium text-sm">Uploaded files</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="p-2">Filename</th>
              <th className="p-2">Type</th>
              <th className="p-2">Status</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {(uploads || []).map((u) => (
              <tr key={u.id} className="border-b border-gray-100">
                <td className="p-2">{u.original_filename}</td>
                <td className="p-2">{u.mime_type}</td>
                <td className="p-2">
                  {u.processing_status}
                  {u.processing_error && (
                    <span className="text-xs text-red-600 ml-2">{u.processing_error}</span>
                  )}
                </td>
                <td className="p-2 text-right">
                  {u.processing_status === "failed" && (
                    <button className="btn-secondary" onClick={() => retry.mutate(u.id)}>
                      Retry
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
