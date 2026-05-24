/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: '../src/sgm/interface/web/static',
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
