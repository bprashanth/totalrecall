import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      // Vinext classifies multipart App Router requests through the server-action reader.
      // Keep that transport ceiling above the paper route's explicit 25 MB product limit.
      bodySizeLimit: "32mb",
    },
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
