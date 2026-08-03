import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { ConfidenceBadge, ReviewBadge } from "@/components/ConfidenceBadge";
import { RecordsTable } from "@/components/RecordsTable";
import { ComplianceBanner } from "@/components/ComplianceBanner";
import type { RecordOut } from "@/types";

describe("match review UI", () => {
  it("renders confidence score and category", () => {
    render(<ConfidenceBadge score={93.5} category="strong" />);
    expect(screen.getByText(/94\/100 · strong/)).toBeInTheDocument();
  });

  it("renders review status", () => {
    render(<ReviewBadge status="needs_more_info" />);
    expect(screen.getByText(/needs more info/)).toBeInTheDocument();
  });
});

describe("records table (search results)", () => {
  const recs: RecordOut[] = [
    {
      id: "1",
      record_type: "court_filing",
      title: "Civil Case - Rivera",
      description: null,
      jurisdiction: "Demo County, DX",
      filing_date: "2023-03-14",
      case_number: "2023-CV-004821",
      original_url: "https://example.gov/x",
      primary_name: "Jonathan A. Rivera",
      normalized_name: "jonathan rivera",
      normalized_address: null,
      city: null,
      state: null,
      zip_code: null,
      is_demo: true,
      created_at: "2023-01-01",
    },
  ];

  it("shows record rows with source link", () => {
    render(<RecordsTable records={recs} />);
    expect(screen.getByText("Civil Case - Rivera")).toBeInTheDocument();
    expect(screen.getByText("2023-CV-004821")).toBeInTheDocument();
    expect(screen.getByText("source")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<RecordsTable records={[]} />);
    expect(screen.getByText(/No records found/)).toBeInTheDocument();
  });
});

describe("compliance banner", () => {
  it("expands details on demand", () => {
    render(<ComplianceBanner />);
    expect(screen.getByText(/does/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Learn more"));
    expect(screen.getByText(/facial recognition/)).toBeInTheDocument();
  });
});
