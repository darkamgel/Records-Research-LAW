"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface Doc {
  id: string;
  title: string | null;
  mime_type: string | null;
  page_count: number;
  char_count: number;
  extraction_quality: number;
  ocr_used: boolean;
  processing_status: string;
  warnings: string[] | null;
}

export default function DocumentsPage() {
  const { data } = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiFetch<Doc[]>("/documents"),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Documents</h1>
      <div className="card">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="p-2">Title</th>
              <th className="p-2">Pages</th>
              <th className="p-2">Chars</th>
              <th className="p-2">Quality</th>
              <th className="p-2">OCR</th>
              <th className="p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((d) => (
              <tr key={d.id} className="border-b border-gray-100">
                <td className="p-2">{d.title || "(untitled)"}</td>
                <td className="p-2">{d.page_count}</td>
                <td className="p-2">{d.char_count}</td>
                <td className="p-2">{(d.extraction_quality * 100).toFixed(0)}%</td>
                <td className="p-2">{d.ocr_used ? "yes" : "no"}</td>
                <td className="p-2">{d.processing_status}</td>
              </tr>
            ))}
            {data && data.length === 0 && (
              <tr>
                <td className="p-4 text-gray-500" colSpan={6}>
                  No documents. Upload a PDF/TXT under Import Data.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
