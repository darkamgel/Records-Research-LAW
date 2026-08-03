import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import GuidePage from "@/app/(app)/guide/page";

describe("user guide page", () => {
  it("shows how to run and use the app with links into key screens", () => {
    render(<GuidePage />);

    expect(screen.getByRole("heading", { name: /user guide/i })).toBeInTheDocument();
    expect(screen.getByText(/demo@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/How to run this software/i)).toBeInTheDocument();
    expect(screen.getByText(/docker compose up --build/)).toBeInTheDocument();

    // Jump links into the real app screens
    expect(screen.getByRole("link", { name: /^Open search$/i })).toHaveAttribute("href", "/search");
    expect(screen.getByRole("link", { name: /^Import data$/ })).toHaveAttribute("href", "/import");
    expect(
      screen.getAllByRole("link", { name: /^Potential Matches$/i }).every((a) => a.getAttribute("href") === "/matches")
    ).toBe(true);
  });
});
