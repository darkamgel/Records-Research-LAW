import { describe, it, expect, vi } from "vitest";
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

import SearchPage from "@/app/(app)/search/page";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("search page", () => {
  it("runs a search and shows results", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          id: "1",
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
      total: 1,
      limit: 25,
      offset: 0,
    });

    wrap(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText(/keyword, phrase/i), {
      target: { value: "Rivera" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => expect(screen.getByText("Civil Case - Rivera")).toBeInTheDocument());
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/records/search",
      expect.objectContaining({ method: "POST" })
    );
    // save-search control is present
    expect(screen.getByPlaceholderText(/save search as/i)).toBeInTheDocument();
  });
});
