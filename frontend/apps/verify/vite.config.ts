import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Mizan Labs — Vérification de documents",
        short_name: "Mizan Vérif",
        description: "Vérifiez l'authenticité d'un document Mizan Labs, même hors ligne.",
        theme_color: "#1F5EFF",
        background_color: "#F6F7F9",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
      },
      workbox: {
        navigateFallback: "/index.html",
        runtimeCaching: [
          { urlPattern: ({ url }) => url.pathname.endsWith("/verify/keys"), handler: "StaleWhileRevalidate", options: { cacheName: "mizan-jwks", expiration: { maxAgeSeconds: 7 * 24 * 3600 } } },
          { urlPattern: ({ url }) => url.pathname.includes("/verify/transparency/head"), handler: "NetworkFirst", options: { cacheName: "mizan-transparency" } },
        ],
      },
    }),
  ],
  build: { sourcemap: true },
  server: { proxy: { "/api": { target: process.env["VITE_API_PROXY"] ?? "http://127.0.0.1:8000", changeOrigin: true } } },
});
