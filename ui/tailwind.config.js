/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Montserrat', 'system-ui', 'sans-serif'],
        body:    ['Roboto', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          orange: "#FF8C00",
          carbon: "#2D2D2D",
          metal:  "#E0E0E0",
          white:  "#FFFFFF",
        },
        jarvis: {
          bg:      "#111111",
          surface: "#1a1a1a",
          card:    "#2D2D2D",
          border:  "#3d3d3d",
          purple:  "#FF8C00",   // Naranja Industrial — todos los usos de purple → orange
          orange:  "#FF8C00",
          teal:    "#1d9e75",
          amber:   "#ef9f27",
          text:    "#F0F0F0",
          muted:   "#9a9a9a",
          metal:   "#E0E0E0",
        }
      }
    }
  },
  plugins: [],
}
