import Link from "next/link";
import type { RecordOut } from "@/types";

export function RecordsTable({
  records,
  selectable,
  selected,
  onToggle,
}: {
  records: RecordOut[];
  selectable?: boolean;
  selected?: Set<string>;
  onToggle?: (id: string) => void;
}) {
  if (records.length === 0)
    return <p className="text-sm text-gray-500 p-4">No records found.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            {selectable && <th className="p-2 w-8"></th>}
            <th className="p-2">Title / Name</th>
            <th className="p-2">Type</th>
            <th className="p-2">Case #</th>
            <th className="p-2">Filed</th>
            <th className="p-2">Jurisdiction</th>
            <th className="p-2">Source</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              {selectable && (
                <td className="p-2">
                  <input
                    type="checkbox"
                    checked={selected?.has(r.id) || false}
                    onChange={() => onToggle?.(r.id)}
                  />
                </td>
              )}
              <td className="p-2">
                <Link href={`/records/${r.id}`} className="text-brand-600 hover:underline">
                  {r.title || r.primary_name || "(untitled)"}
                </Link>
                {r.is_demo && (
                  <span className="badge bg-gray-100 text-gray-600 ml-2">demo</span>
                )}
                {r.primary_name && r.title && (
                  <div className="text-xs text-gray-500">{r.primary_name}</div>
                )}
              </td>
              <td className="p-2">{r.record_type || "-"}</td>
              <td className="p-2">{r.case_number || "-"}</td>
              <td className="p-2">{r.filing_date || "-"}</td>
              <td className="p-2">{r.jurisdiction || "-"}</td>
              <td className="p-2">
                {r.original_url ? (
                  <a
                    href={r.original_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-600 hover:underline"
                  >
                    source
                  </a>
                ) : (
                  "-"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
