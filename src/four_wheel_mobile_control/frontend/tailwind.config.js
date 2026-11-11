/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        pixel: ['"Press Start 2P"', '"Courier New"', 'monospace'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        arcade: {
          bg: '#0F0F23',
          panel: '#080818',
          panelAlt: '#11112B',
          blue: '#0000FF',
          blueHeader: '#1028C8',
          red: '#FF0000',
          redDark: '#B80000',
          green: '#00FF00',
          yellow: '#FFFF00',
          white: '#FFFFFF',
          black: '#000000',
        },
      },
      boxShadow: {
        pixel: '3px 3px 0px #000000',
        'pixel-sm': '2px 2px 0px #000000',
        'pixel-lg': '4px 4px 0px #000000',
      },
    },
  },
  plugins: [],
};
