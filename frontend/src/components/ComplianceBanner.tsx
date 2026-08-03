"use client";

import { useState } from "react";

export function ComplianceBanner() {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-amber-50 border-b border-amber-200 text-amber-900 text-xs">
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-start gap-2">
        <span className="font-semibold">Research tool notice:</span>
        <span className="flex-1">
          Operates only on public or user-uploaded data. AI summaries and match
          suggestions are labeled and require human review. This tool does{" "}
          <strong>not</strong> make identity determinations and must not be used for
          legal, employment, housing, credit, insurance, immigration, educational, or
          law-enforcement decisions.
          {open && (
            <span className="block mt-1">
              It does not bypass authentication, CAPTCHAs, or rate limits; it prefers
              official APIs, bulk downloads, and RSS feeds; it preserves source
              provenance; and it does not infer protected characteristics or use facial
              recognition.
            </span>
          )}
        </span>
        <button className="underline whitespace-nowrap" onClick={() => setOpen((v) => !v)}>
          {open ? "Show less" : "Learn more"}
        </button>
      </div>
    </div>
  );
}
