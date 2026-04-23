import basicSsl from "@vitejs/plugin-basic-ssl"
import tailwindcss from "@tailwindcss/vite"

// https://nuxt.com/docs/api/configuration/nuxt-config
const useHttps = process.env.NUXT_HTTPS === "true"

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  css: ["~/assets/main.css"],
  modules: ["@nuxtjs/i18n"],
  i18n: {
    strategy: "prefix",
    defaultLocale: "en",
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: "schedra_locale",
      redirectOn: "root",
    },
    locales: [
      { code: "en", iso: "en-US", name: "English", file: "en.json" },
      { code: "vi", iso: "vi-VN", name: "Tieng Viet", file: "vi.json" },
    ],
    lazy: true,
    langDir: "locales",
  },
  app: {
    head: {
      link: [
        { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      ],
    },
  },
  devServer: {
    host: process.env.NUXT_HOST || "0.0.0.0",
    port: Number(process.env.NUXT_PORT || 3000),
    https: useHttps,
  },
  runtimeConfig: {
    backendBase: process.env.NUXT_BACKEND_BASE || "http://127.0.0.1:8000",
  },
  vite: {
    plugins: [tailwindcss(), ...(useHttps ? [basicSsl()] : [])],
    resolve: {
      // Prevent duplicate useAppConfig warning from nitropack vs @nuxt/nitro-server
      dedupe: ["nitropack", "@nuxt/nitro-server"],
    },
  },
})
