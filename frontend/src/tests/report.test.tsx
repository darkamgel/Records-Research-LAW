import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  API_URL: "http://test",
  getToken: () => "t",
  getWorkspace: () => "w",
}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "proj-1" }),
}));

import ProjectDetailPage from "@/app/(app)/projects/[id]/page";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const project = {
  id: "proj-1",
  name: "Rivera estate research",
  objective: "Trace related public filings for the Rivera estate.",
  records: [],
};

describe("research report generation", () => {
  beforeEach(() => apiFetchMock.mockReset());

  it("generates a cited summary report and exposes export formats", async () => {
    apiFetchMock.mockImplementation((path: string, opts?: { method?: string }) => {
      if (path === "/projects/proj-1") return Promise.resolve(project);
      if (path === "/projects/proj-1/report" && opts?.method === "POST")
        return Promise.resolve({
          id: "rep-1",
          title: "Research summary",
          summary_markdown:
            "# Research summary\n\nSources reviewed: Demo County records [record:a].\n\n_AI-assisted; subject to human review._",
          ai_generated: true,
        });
      return Promise.resolve({});
    });

    wrap(<ProjectDetailPage />);
    await waitFor(() =>
      expect(screen.getByText("Rivera estate research")).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole("button", { name: /generate report/i }));

    await waitFor(() =>
      expect(screen.getByText(/Sources reviewed: Demo County records/)).toBeInTheDocument()
    );
    // AI label + all export formats present.
    expect(screen.getByText("AI-assisted")).toBeInTheDocument();
    for (const fmt of ["markdown", "json", "csv", "html"]) {
      expect(screen.getByRole("button", { name: new RegExp(`export ${fmt}`, "i") })).toBeInTheDocument();
    }
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/projects/proj-1/report",
      expect.objectContaining({ method: "POST", body: expect.objectContaining({ use_ai: true }) })
    );
  });
});
