/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
      },
      colors: {
        ink: {
          950: "#0c1220",
          900: "#121a2b",
          800: "#1b2438",
        },
        accent: {
          500: "#d97706",
          600: "#b45309",
        },
      },
    },
  },
  plugins: [],
};
