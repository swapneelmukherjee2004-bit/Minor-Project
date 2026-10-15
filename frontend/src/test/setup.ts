import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());

// jsdom lacks these; Recharts / Radix need them.
class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO;
window.matchMedia = window.matchMedia || ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }));
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {});

if (typeof window.localStorage === "undefined" || !window.localStorage.clear) {
  const store = new Map<string, string>();
  const mockStorage: Storage = {
    length: 0,
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (key: string) => store.delete(key),
    setItem: (key: string, value: string) => store.set(key, String(value)),
  };
  Object.defineProperty(window, "localStorage", { value: mockStorage, writable: true });
}

