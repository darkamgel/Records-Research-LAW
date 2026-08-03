import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

const loginSpy = vi.fn().mockResolvedValue(undefined);

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ login: loginSpy, register: vi.fn(), logout: vi.fn(), user: null, loading: false }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import LoginPage from "@/app/login/page";

describe("login page", () => {
  beforeEach(() => loginSpy.mockClear());

  it("renders and submits credentials", async () => {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("email"), { target: { value: "demo@example.com" } });
    fireEvent.change(screen.getByLabelText("password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(loginSpy).toHaveBeenCalledWith("demo@example.com", "password123"));
  });

  it("blocks submission when the email is invalid", async () => {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("email"), { target: { value: "not-an-email" } });
    fireEvent.change(screen.getByLabelText("password"), { target: { value: "password123" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    });
    // Client-side schema validation must prevent the login call for an invalid email.
    expect(loginSpy).not.toHaveBeenCalled();
  });
});
