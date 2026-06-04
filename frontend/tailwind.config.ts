import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        leaf: {
          50: "#f2fbf4",
          100: "#e0f7e5",
          200: "#bfefca",
          300: "#8fe0a5",
          400: "#56c97b",
          500: "#2fb25c",
          600: "#1f9147",
          700: "#1a723b",
          800: "#185a32",
          900: "#154a2b",
          950: "#082816",
        },
        canvas: {
          DEFAULT: "#0b1410",
          soft: "#0f1c17",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 10px 40px -10px rgba(47, 178, 92, 0.35)",
        card: "0 10px 30px -10px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 20% 0%, rgba(47,178,92,0.18), transparent 40%), radial-gradient(circle at 90% 10%, rgba(47,178,92,0.08), transparent 45%)",
      },
      borderRadius: {
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
    },
  },
  plugins: [],
};

export default config;
