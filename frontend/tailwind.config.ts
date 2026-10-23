import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        teleprompter: {
          bg: "#050505",
          card: "#121212",
          border: "#262626",
          cyan: "#00F0FF",
          green: "#00FF66",
          yellow: "#FFD600",
          red: "#FF334B",
          muted: "#888888",
        },
      },
    },
  },
  plugins: [],
};
export default config;
