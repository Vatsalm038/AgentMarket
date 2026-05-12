/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Inter as the default sans — body, headings, nav
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        // JetBrains Mono for IDs, signatures, code, JSON
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
