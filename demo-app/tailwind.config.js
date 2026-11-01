/** Tokens live in src/index.css as CSS variables (light + dark); Tailwind only maps names to them. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)", sheet: "var(--sheet)", rule: "var(--rule)", ink: "var(--ink)", soft: "var(--soft)",
        pen: "var(--pen)", penwash: "var(--penwash)", ok: "var(--ok)", okwash: "var(--okwash)",
        hold: "var(--hold)", holdwash: "var(--holdwash)", bad: "var(--bad)", badwash: "var(--badwash)", code: "var(--code)",
      },
      fontFamily: {
        sans: ['"Schibsted Grotesk"', '"Noto Sans SC"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
};
