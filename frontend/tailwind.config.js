/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ICPAC brand colors
        'icpac-green': '#034930',
        'icpac-dark': '#023020',
        
        // Alert status colors
        'alert-normal': '#2ecc71',
        'alert-warning': '#f39c12',
        'alert-alarm': '#e67e22',
        'alert-emergency': '#e74c3c',
      },
      spacing: {
        'navbar': '80px',
        'sidebar': '350px',
      },
      zIndex: {
        'navbar': '1100',
        'sidebar': '998',
        'map-controls': '1000',
      }
    },
  },
  plugins: [],
  // Don't conflict with MUI
  corePlugins: {
    preflight: false,
  },
}
