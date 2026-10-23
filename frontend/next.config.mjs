/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: false,
  webpack: (config) => {
    return config;
  },
};

export default nextConfig;
