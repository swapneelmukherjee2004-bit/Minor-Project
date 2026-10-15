/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)", surface: "rgb(var(--surface) / <alpha-value>)",
        subtle: "rgb(var(--subtle) / <alpha-value>)", fg: "rgb(var(--fg) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)", line: "rgb(var(--line) / <alpha-value>)",
        brand: "rgb(var(--brand) / <alpha-value>)", "brand-fg": "rgb(var(--brand-fg) / <alpha-value>)",
        conv: "rgb(var(--conv) / <alpha-value>)", ai: "rgb(var(--ai) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)", warn: "rgb(var(--warn) / <alpha-value>)", ok: "rgb(var(--ok) / <alpha-value>)",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgb(0 0 0 / 0.04), 0 1px 3px rgb(0 0 0 / 0.06)" },
    },
  },
  plugins: [],
};
