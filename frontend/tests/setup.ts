import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

// React-router uses scrollTo on navigation in some environments; jsdom doesn't implement it.
window.scrollTo = vi.fn() as typeof window.scrollTo;

// jsdom doesn't implement URL.createObjectURL / revokeObjectURL.
Object.defineProperty(URL, "createObjectURL", { value: () => "blob://test", writable: true });
Object.defineProperty(URL, "revokeObjectURL", { value: () => {}, writable: true });

// Reset DOM + localStorage between tests
afterEach(() => {
  localStorage.clear();
});
