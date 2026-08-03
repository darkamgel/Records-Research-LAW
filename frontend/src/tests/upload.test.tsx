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

import ImportPage from "@/app/(app)/import/page";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("import / file upload page", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("lists available source adapters with access method and attribution", async () => {
    apiFetchMock.mockResolvedValue([
      {
        source_key: "csv_upload",
        source_name: "CSV Upload",
        source_type: "upload",
        access_method: "user_upload",
        terms_notes: "User-provided files only.",
        attribution: "User upload",
        requires_auth: false,
        rate_limit_per_minute: null,
      },
    ]);

    wrap(<ImportPage />);
    await waitFor(() => expect(screen.getByText("CSV Upload")).toBeInTheDocument());
    expect(screen.getByText("user_upload")).toBeInTheDocument();
    expect(screen.getByText(/Attribution: User upload/)).toBeInTheDocument();
  });

  it("uploads a selected file via multipart and shows a success message", async () => {
    apiFetchMock.mockResolvedValue([]); // adapters query
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    wrap(<ImportPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["name,case_number\nJane Doe,2024-CV-1"], "records.csv", {
      type: "text/csv",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /upload & process/i }));

    await waitFor(() => expect(screen.getByText(/File uploaded and processed/)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://test/files/upload",
      expect.objectContaining({ method: "POST" })
    );
    const body = (fetchMock.mock.calls[0][1] as { body: FormData }).body;
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("triggers a demonstration-data import", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/sources/adapters") return Promise.resolve([]);
      if (path === "/sources") return Promise.resolve({ id: "src-1" });
      if (path === "/sources/src-1/import") return Promise.resolve({ records_created: 8 });
      return Promise.resolve({});
    });

    wrap(<ImportPage />);
    fireEvent.click(screen.getByRole("button", { name: /import demo records/i }));
    await waitFor(() =>
      expect(screen.getByText(/Imported 8 demonstration records/)).toBeInTheDocument()
    );
  });
});
