module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          50: '#e6f7f3',
          100: '#c1f0e5',
          200: '#99e9d7',
          300: '#4dd9bb',
          400: '#26b28e',
          500: '#1a8c70',
          600: '#146f58',
          700: '#0f553f',
          800: '#0b3e2a',
          900: '#07291b',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
      },
      animation: {
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      }
    },
  },
  plugins: [],
}
