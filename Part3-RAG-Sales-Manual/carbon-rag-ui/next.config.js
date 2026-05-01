/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'newsroom.ibm.com',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'assets.ibm.com',
        port: '',
        pathname: '/**',
      },
    ],
  },
  // Increase API route timeout for LLM generation (default is 60s)
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },
  // Set longer timeout for API routes (5 minutes)
  serverRuntimeConfig: {
    apiTimeout: 300000, // 5 minutes in milliseconds
  },
};

module.exports = nextConfig;