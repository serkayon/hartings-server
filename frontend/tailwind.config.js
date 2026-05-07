/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          50: '#f8fafc',
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        }
      }
    },
  },
  plugins: [],
}
