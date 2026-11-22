import type { NextConfig } from "next";

const config: NextConfig = {
  poweredByHeader: false,
  // Local dev only: on Vercel the top-level rewrite sends /api to the FastAPI service.
  async rewrites() {
    if (process.env.VERCEL) return [];
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
  },
};

export default config;
