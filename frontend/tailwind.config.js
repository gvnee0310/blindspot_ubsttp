/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: '#FBF9F4', raised: '#FFFFFF', sunk: '#F3EFE6' },
        ink: { DEFAULT: '#1A1D21', soft: '#4A4E55', faint: '#8A8E96', line: '#E4DFD4' },
        teal: { 50: '#E6F2F1', 100: '#C6E3E1', 400: '#2A9D8F', 600: '#0E7C7B', 700: '#0A5F5E', 900: '#063E3D' },
        amber: { 100: '#F7E6C9', 500: '#E0913A', 700: '#B06E22' },
        clay: { 100: '#F1D9CF', 500: '#C56A4E', 700: '#9E4E36' },
        balance: { 100: '#D4EAD0', 500: '#5FA357', 700: '#3E7A38' },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(26,29,33,0.04), 0 4px 16px rgba(26,29,33,0.06)',
        lift: '0 2px 4px rgba(26,29,33,0.06), 0 12px 32px rgba(26,29,33,0.10)',
      },
      borderRadius: { xl2: '1.25rem' },
    },
  },
  plugins: [],
};
