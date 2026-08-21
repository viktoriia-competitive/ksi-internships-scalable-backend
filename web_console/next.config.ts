import type { NextConfig } from "next";

const production = process.env.NODE_ENV === "production";

const config: NextConfig = {
  output: production ? "standalone" : undefined,
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
};

export default config;
