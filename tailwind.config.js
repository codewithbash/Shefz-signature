/** SHEFz Signature: Tailwind config (brand colours and fonts live here). */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/**/*.py",
    "./node_modules/flowbite/**/*.js",
  ],
  // Words that only appear in Python (flash message categories)
  safelist: ["success", "error", "pending", "confirmed", "in_production", "ready",
    "delivered", "cancelled", "unpaid", "paid", "refunded"],
  // Preflight (Tailwind's reset) is off for now so the current design
  // looks exactly the same. Turn it on later when pages are fully converted.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        ink: "#0f0e0d",
        surface: "#1a1816",
        line: "#2a2622",
        gold: { DEFAULT: "#c9a96a", light: "#e0c48a" },
        cream: "#f5f0e8",
        muted: "#a39a8c",
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', "Georgia", "serif"],
        sans: ['"Jost"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("flowbite/plugin")], // used on admin pages
};
