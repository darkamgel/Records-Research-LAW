import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe6ff",
          500: "#3b6ef6",
          600: "#2f5ae0",
          700: "#2647b0",
        },
      },
    },
  },
  plugins: [],
};

export default config;
