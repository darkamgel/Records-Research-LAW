import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

import MatchesPage from "@/app/(app)/matches/page";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const candidate = {
  id: "cand-1",
  confidence_score: 88.2,
  category: "strong",
  review_status: "not_reviewed",
  rationale: "Same normalized last name and shared ZIP code.",
  rationale_source: "deterministic",
  supporting_evidence: [{ detail: "Exact last-name match" }],
  conflicting_evidence: [{ detail: "Different middle initial" }],
  missing_information: ["date_of_birth"],
  record_a: {
    id: "a",
    title: "Civil Case - Rivera",
    primary_name: "Jonathan A. Rivera",
    case_number: "2023-CV-004821",
    filing_date: "2023-03-14",
    normalized_address: "12 main st",
    jurisdiction: "Demo County",
    original_url: "https://example.gov/a",
  },
  record_b: {
    id: "b",
    title: "Probate - Rivera",
    primary_name: "Jon Rivera",
    case_number: "2024-PR-100",
    filing_date: "2024-01-02",
    normalized_address: "12 main st",
    jurisdiction: "Demo County",
    original_url: "https://example.gov/b",
  },
};

describe("match review workflow", () => {
  beforeEach(() => apiFetchMock.mockReset());

  it("shows candidates with explainable confidence and review status", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/matches?limit=100") return Promise.resolve([candidate]);
      return Promise.resolve({});
    });

    wrap(<MatchesPage />);
    await waitFor(() =>
      expect(screen.getByText(/Same normalized last name/)).toBeInTheDocument()
    );
    expect(screen.getByText(/88\/100 · strong/)).toBeInTheDocument();
  });

  it("opens side-by-side review and submits a confirm decision", async () => {
    apiFetchMock.mockImplementation((path: string, opts?: { method?: string }) => {
      if (path === "/matches?limit=100") return Promise.resolve([candidate]);
      if (path === "/matches/cand-1") return Promise.resolve(candidate);
      if (path === "/matches/cand-1/review" && opts?.method === "POST")
        return Promise.resolve({ ok: true });
      return Promise.resolve({});
    });

    wrap(<MatchesPage />);
    await waitFor(() => screen.getByRole("button", { name: /review/i }));
    fireEvent.click(screen.getByRole("button", { name: /review/i }));

    // Side-by-side records + evidence visible in the modal.
    await waitFor(() => expect(screen.getByText(/Review potential match/)).toBeInTheDocument());
    expect(screen.getByText("Jonathan A. Rivera")).toBeInTheDocument();
    expect(screen.getByText("Jon Rivera")).toBeInTheDocument();
    expect(screen.getByText("Exact last-name match")).toBeInTheDocument();
    expect(screen.getByText("Different middle initial")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirm for project/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/matches/cand-1/review",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ decision: "confirmed" }),
        })
      )
    );
  });
});
