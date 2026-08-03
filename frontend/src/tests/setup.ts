import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Provide a default fetch mock; individual tests can override.
if (!globalThis.fetch) {
  globalThis.fetch = vi.fn();
}
