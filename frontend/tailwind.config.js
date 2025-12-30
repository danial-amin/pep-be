/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pastel-pink': '#FFB6C1',
        'pastel-blue': '#ADD8E6',
        'pastel-purple': '#DDA0DD',
        'pastel-green': '#90EE90',
        'pastel-yellow': '#FFFFE0',
        'pastel-orange': '#FFDAB9',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}

