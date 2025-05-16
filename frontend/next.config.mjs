/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/google/:path*',
        destination: 'http://localhost:8000/google/:path*',
      },
      {
        source: '/api/stripe/:path*',
        destination: 'http://localhost:8000/stripe/:path*',
      },
    ];
  },
};

export default nextConfig;