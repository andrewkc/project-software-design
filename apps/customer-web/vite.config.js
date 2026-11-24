import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// operations-web usa 5173; este puerto evita que ambas apps compartan localStorage.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, strictPort: true },
  test: { environment: "jsdom", globals: false },
});
