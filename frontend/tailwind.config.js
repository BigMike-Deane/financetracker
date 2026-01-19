/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e8f4fd',
          100: '#d1e9fb',
          200: '#a3d3f7',
          300: '#75bdf3',
          400: '#47a7ef',
          500: '#1991eb',
          600: '#1474bc',
          700: '#0f578d',
          800: '#0a3a5e',
          900: '#051d2f',
        },
        dark: {
          50: '#f5f5f7',
          100: '#e5e5ea',
          200: '#c7c7cc',
          300: '#aeaeb2',
          400: '#8e8e93',
          500: '#636366',
          600: '#48484a',
          700: '#363638',
          800: '#2c2c2e',
          900: '#1c1c1e',
          950: '#0a0a0c',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
