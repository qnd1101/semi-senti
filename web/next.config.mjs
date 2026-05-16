/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverComponentsExternalPackages: ["sql.js"],
  },
  async rewrites() {
    const pythonApi = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/py-api/:path*",
        destination: `${pythonApi}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
