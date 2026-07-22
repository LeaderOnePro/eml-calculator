import type { NextConfig } from "next";

// In dev, the Python backend (FastAPI via uvicorn) runs separately on :8000.
// We proxy /api/* to it so the browser sees same-origin requests (no CORS).
// On Vercel, /api/* is served natively by the Python serverless function,
// so this rewrite only applies in development.
const API_BACKEND = process.env.API_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [{ source: "/api/:path*", destination: `${API_BACKEND}/api/:path*` }];
    }
    return [];
  },
};

export default nextConfig;
