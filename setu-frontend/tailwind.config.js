/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cyan:  { 400: '#00f2fe', 500: '#00d4e0' },
        space: { 900: '#06060a', 800: '#0a0d14', 700: '#0d1117', 600: '#111827' },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'scan':       'scan 4s linear infinite',
        'glow':       'glow 2s ease-in-out infinite alternate',
        'blink':      'blink 1s step-end infinite',
        'slide-up':   'slideUp 0.6s ease forwards',
        'fade-in':    'fadeIn 0.5s ease forwards',
      },
      keyframes: {
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        glow: {
          from: { textShadow: '0 0 8px #00f2fe' },
          to:   { textShadow: '0 0 24px #00f2fe, 0 0 48px #00f2fe' },
        },
        blink: {
          '0%,100%': { opacity: '1' },
          '50%':     { opacity: '0' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}