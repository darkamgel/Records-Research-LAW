import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import SavedSearchesPage from "@/app/(app)/saved-searches/page";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const saved = {
  id: "ss-1",
  name: "Rivera filings",
  last_executed_at: null,
  last_result_count: null,
};

describe("saved searches", () => {
  beforeEach(() => apiFetchMock.mockReset());

  it("lists saved searches and re-runs one, showing change summary", async () => {
    apiFetchMock.mockImplementation((path: string, opts?: { method?: string }) => {
      if (path === "/saved-searches" && (!opts || opts.method !== "DELETE"))
        return Promise.resolve([saved]);
      if (path === "/saved-searches/ss-1/execute")
        return Promise.resolve({
          result_count: 2,
          new_result_ids: ["r2"],
          removed_result_ids: [],
          items: [
            {
              id: "r2",
              title: "Civil Case - Rivera",
              record_type: "court_filing",
              case_number: "2023-CV-004821",
              filing_date: "2023-03-14",
              jurisdiction: "Demo County",
              original_url: null,
              primary_name: "Jonathan Rivera",
              is_demo: false,
            },
          ],
        });
      return Promise.resolve({});
    });

    wrap(<SavedSearchesPage />);
    await waitFor(() => expect(screen.getByText("Rivera filings")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^run$/i }));

    await waitFor(() => expect(screen.getByText(/2 results/)).toBeInTheDocument());
    expect(screen.getByText(/1 new/)).toBeInTheDocument();
    expect(screen.getByText("Civil Case - Rivera")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/saved-searches/ss-1/execute",
      expect.objectContaining({ method: "POST" })
    );
  });
});
