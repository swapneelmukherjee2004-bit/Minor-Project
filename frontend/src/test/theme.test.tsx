import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, beforeEach } from "vitest";
import { ThemeToggle } from "@/components/ThemeToggle";
import { renderApp } from "./utils";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = "";
  });

  it("toggles theme between dark and light mode", async () => {
    renderApp(<ThemeToggle />);
    const btn = screen.getByRole("button");

    // Initially checks preference (defaults to dark or system)
    const initialLabel = btn.getAttribute("aria-label");
    expect(initialLabel).toMatch(/Switch to (light|dark) mode/);

    await userEvent.click(btn);
    const toggledLabel = btn.getAttribute("aria-label");
    expect(toggledLabel).not.toBe(initialLabel);

    await userEvent.click(btn);
    expect(btn.getAttribute("aria-label")).toBe(initialLabel);
  });
});
