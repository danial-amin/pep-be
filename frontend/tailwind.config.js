/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'accent': '#d4763b',
        'accent-hover': '#c46830',
        'accent-light': '#fef3ec',
        'surface': '#ffffff',
        'base': '#f8f7f4',
        'subtle': '#f0efe9',
        'muted-border': '#e5e3dc',
      },
    },
  },
  plugins: [],
}
