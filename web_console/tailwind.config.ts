import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0c0f",
          900: "#111419",
          800: "#1a1f27",
        },
        paper: {
          50: "#f7f7f4",
          100: "#efefe9",
        },
        brand: {
          50: "#fff3ed",
          100: "#ffe1d2",
          500: "#ff6b35",
          600: "#e95825",
          700: "#bf4319",
          900: "#70270f",
        },
      },
      boxShadow: {
        panel: "0 18px 60px rgba(16, 24, 40, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
