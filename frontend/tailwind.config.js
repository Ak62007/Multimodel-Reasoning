/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: ["Fraunces", "Georgia", "Cambria", "serif"],
      },
      maxWidth: {
        report: "768px",
      },
      colors: {
        // Single soft, muted accent — warm champagne/sand (no neon).
        sand: "#cbb491",
        // Semantic accents per spec §8.4
        tone: {
          strong: "#16a34a",   // green-600
          authentic: "#22c55e", // green-500
          neutral: "#6b7280",  // gray-500
          mixed: "#d97706",    // amber-600
          concerning: "#dc2626", // red-600
        },
      },
    },
  },
  plugins: [],
};
