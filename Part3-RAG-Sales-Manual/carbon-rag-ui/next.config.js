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
    // Disable ISR (Incremental Static Regeneration) to prevent cache writes
    isrMemoryCacheSize: 0,
  },
  // Set longer timeout for API routes (5 minutes)
  serverRuntimeConfig: {
    apiTimeout: 300000, // 5 minutes in milliseconds
  },
  // Disable all caching to prevent browser storage issues
  // This is critical for API routes that proxy to backend services
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store, no-cache, must-revalidate, max-age=0' },
          { key: 'Pragma', value: 'no-cache' },
          { key: 'Expires', value: '0' },
        ],
      },
    ];
  },
  // Disable on-demand ISR and caching completely
  onDemandEntries: {
    maxInactiveAge: 0,
    pagesBufferLength: 0,
  },
};

module.exports = nextConfig;