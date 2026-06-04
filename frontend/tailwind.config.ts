import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#17221f",
        mineral: "#58716c",
        sage: "#8eb7a9",
        celadon: "#dceee6",
        pollen: "#f4d06f",
        coral: "#db6f5d",
        clay: "#a45f55"
      },
      boxShadow: {
        lens: "0 24px 70px rgba(37, 66, 62, 0.16)"
      }
    }
  },
  plugins: []
};

export default config;

