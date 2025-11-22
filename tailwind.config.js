module.exports = {
  content: [
    "./pages/*.{html,js}",
    "./index.html",
    "./src/**/*.{html,js}",
    "./*.html"
  ],
  theme: {
    extend: {
      colors: {
        // Primary Colors - Electric Intelligence
        primary: {
          DEFAULT: "#0066FF", // custom blue
          50: "#EFF6FF", // blue-50
          100: "#DBEAFE", // blue-100
          500: "#3B82F6", // blue-500
          600: "#0066FF", // custom blue
          700: "#1D4ED8", // blue-700
          900: "#1E3A8A", // blue-900
        },
        // Secondary Colors - Creative Transformation
        secondary: {
          DEFAULT: "#8B5CF6", // violet-500
          50: "#F5F3FF", // violet-50
          100: "#EDE9FE", // violet-100
          400: "#A78BFA", // violet-400
          500: "#8B5CF6", // violet-500
          600: "#7C3AED", // violet-600
          700: "#6D28D9", // violet-700
        },
        // Accent Colors - Success Celebration
        accent: {
          DEFAULT: "#10B981", // emerald-500
          50: "#ECFDF5", // emerald-50
          100: "#D1FAE5", // emerald-100
          500: "#10B981", // emerald-500
          600: "#059669", // emerald-600
        },
        // Background Colors - Clean Canvas
        background: "#FAFBFC", // slate-50
        surface: "#F8FAFC", // slate-50
        // Text Colors - Professional Clarity
        text: {
          primary: "#1F2937", // gray-800
          secondary: "#6B7280", // gray-500
          muted: "#9CA3AF", // gray-400
        },
        // Status Colors
        success: "#059669", // emerald-600
        warning: "#D97706", // amber-600
        error: "#DC2626", // red-600
        // Border Colors
        border: {
          DEFAULT: "#E5E7EB", // gray-200
          light: "#F3F4F6", // gray-100
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        outfit: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1.2' }],
        '6xl': ['3.75rem', { lineHeight: '1.2' }],
      },
      boxShadow: {
        'soft': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'strong': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      animation: {
        'smooth': 'all 300ms ease-out',
        'transform': 'all 400ms ease-in-out',
      },
      transitionDuration: {
        '300': '300ms',
        '400': '400ms',
      },
      transitionTimingFunction: {
        'ease-out': 'ease-out',
        'ease-in-out': 'ease-in-out',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      },
    },
  },
  plugins: [],
}