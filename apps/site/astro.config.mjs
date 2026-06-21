import { defineConfig } from "astro/config";
import vercel from "@astrojs/vercel";

export default defineConfig({
  output: "server",
  adapter: vercel(),
  server: {
    port: 4321,
  },
  vite: {
    server: {
      open: false,
    },
  },
});
