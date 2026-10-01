/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './components/**/*.html',
    './static/js/modules/**/*.js',
    './static/js/*.js',
    './js/modules/**/*.js',
    './anki.html',
    './index.html',
  ],
  theme: {
    extend: {
      colors: {
        washi: '#FAF8F5',
        hinoki: '#F4EFE6',
        kurogane: '#181A1B',
        shu: '#C23B22',
        aizome: '#1E2C3A',
        matcha: '#264332',
      },
      fontFamily: {
        serif: ['Cinzel', 'Georgia', 'serif'],
        sans: ['"Roboto"', '"Plus Jakarta Sans"', '-apple-system', 'sans-serif'],
        mono: ['"Space Mono"', 'ui-monospace', 'monospace'],
        jp: [
          "'textbook'",
          "'_HGSKyokashotai'",
          "'BIZ UDPMincho'",
          "'Noto Serif JP'",
          'serif',
        ],
      },
    },
  },
  plugins: [],
};
