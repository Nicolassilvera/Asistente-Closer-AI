/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg:      "#0f0f13",
          surface: "#1a1a24",
          card:    "#22222f",
          border:  "#2e2e40",
          purple:  "#7c6ff7",
          teal:    "#1d9e75",
          amber:   "#ef9f27",
          coral:   "#d85a30",
          text:    "#e2e0f0",
          muted:   "#8884a8",
        }
      }
    }
  },
  plugins: [],
}
