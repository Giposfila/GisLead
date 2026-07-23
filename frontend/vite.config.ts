import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    // Package-relative, not repo-relative: this dir ships inside the wheel
    // (see [tool.hatch.build] artifacts in pyproject.toml) so a pipx/wheel
    // install serves the real UI instead of main.py's placeholder page.
    outDir: "../leadgis/webui",
    emptyOutDir: true,
  },
});
