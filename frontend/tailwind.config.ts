import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#fdf6e3",
        ink: "#000000",
        amber: "#ffbf00",
        coral: "#ff6b57",
        candy: "#ff8ad8",
        lime: "#7ee081",
        sky: "#7cc6ff",
      },
      borderWidth: { brutal: "3px" },
      boxShadow: {
        brutal: "6px 6px 0 #000",
        "brutal-sm": "3px 3px 0 #000",
        "brutal-lg": "10px 10px 0 #000",
        none: "none",
      },
      borderRadius: { none: "0" },
    },
  },
  plugins: [],
};
export default config;
