/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: '#111827',
        beige: '#f3f0e8',
        'warm-white': '#fffdf9',
        coral: '#ff5c35',
        'brand-blue': '#3157d5',
        'brand-green': '#39a86b',
      },
    },
  },
  plugins: [],
};
