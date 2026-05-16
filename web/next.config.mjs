/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // sql.js: WASM 기반 SQLite (네이티브 바인딩 없음, T-051)
    serverComponentsExternalPackages: ["sql.js"],
  },
};

export default nextConfig;
