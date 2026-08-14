/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#F7F8F4',
        surface: '#FFFFFF',
        ink: {
          primary: '#14251C',
          secondary: '#5B6B60',
        },
        brand: {
          primary: '#2E6B4F',
          accent: '#C98A3D',
        },
        status: {
          good: '#3A8F6B',
          warn: '#D98B3D',
          risk: '#C1503C',
        },
        criterion: {
          climate: '#4C8C5F',
          soil: '#8B6A4A',
          water: '#3E7FA6',
          market: '#A9752E',
        },
      },
      fontFamily: {
        display: ['"Fraunces"', 'serif'],
        body: ['"Inter"', 'sans-serif'],
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,37,28,0.06), 0 8px 24px rgba(20,37,28,0.06)',
      },
    },
  },
  plugins: [],
};
