/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#0d1117',
          panel: '#161b22',
          border: '#30363d',
          accent: '#00d4ff',
          neon: '#58a6ff',
          alert: '#f85149',
          success: '#3fb950',
          warning: '#d29922'
        }
      }
    },
  },
  plugins: [],
}

