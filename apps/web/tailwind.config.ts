/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Estos son los defaults — se sobreescriben en runtime vía CSS custom properties
        brand: {
          primary: "var(--color-primary, #1a365d)",
          secondary: "var(--color-secondary, #2b6cb0)",
          accent: "var(--color-accent, #e53e3e)",
          background: "var(--color-background, #f7fafc)",
          surface: "var(--color-surface, #ffffff)",
          "text-primary": "var(--color-text-primary, #1a202c)",
          "text-secondary": "var(--color-text-secondary, #718096)",
          success: "var(--color-success, #38a169)",
          warning: "var(--color-warning, #d69e2e)",
          error: "var(--color-error, #e53e3e)",
        },
      },
    },
  },
  plugins: [],
};
