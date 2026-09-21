import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        risk: {
          high: { DEFAULT: '#ef4444', bg: '#450a0a' },
          elevated: { DEFAULT: '#f97316', bg: '#431407' },
          moderate: { DEFAULT: '#eab308', bg: '#422006' },
          low: { DEFAULT: '#22c55e', bg: '#052e16' },
        },
        confidence: {
          high: '#34d399',
          medium: '#facc15',
          low: '#f87171',
        },
        family: {
          execution: '#a78bfa',
          negative: '#22d3ee',
          peer: '#60a5fa',
          anomaly: '#fb923c',
          composite: '#f472b6',
        },
        gov: {
          navy: '#123B5D',
          blue: '#1F5F8B',
          light: '#EAF3F8',
          bg: '#F8FAFC',
          text: '#1F2933',
          muted: '#52606D',
          border: '#D9E2EC',
          saffron: '#FF9933',
          green: '#138808',
        },
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [animate],
};

export default config;
