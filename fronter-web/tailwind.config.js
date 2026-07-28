/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        counter: { bg: "#14100c", panel: "#1e1813", line: "#33291f", text: "#f4ede2", dim: "#9a8b78" },
        route: { build: "#12a594", clarify: "#e0a43b", reject: "#d9694e" },
      },
      keyframes: {
        rise: { "0%": { opacity: 0, transform: "translateY(8px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        pulse2: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.35 } },
      },
      animation: { rise: "rise .35s ease-out both", pulse2: "pulse2 1s ease-in-out infinite" },
    },
  },
  plugins: [],
};
