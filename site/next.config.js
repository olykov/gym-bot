/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000'],
    },
  },
  images: {
    domains: ['localhost'],
    unoptimized: true,
  },
  output: 'standalone',
}

module.exports = nextConfig
