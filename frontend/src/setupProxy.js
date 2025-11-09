const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const target = process.env.REACT_APP_API_TARGET || 'https://takeabreak-app-38abv.ondigitalocean.app';

  const commonProxyOptions = {
    target,
    changeOrigin: true,
    secure: true,
    logLevel: 'warn',
    onProxyReq: (proxyReq, req, res) => {
      // Encourage JSON responses from the backend
      proxyReq.setHeader('Accept', 'application/json');
      // Forward original host for better backend routing if needed
      if (req.headers.host) proxyReq.setHeader('X-Forwarded-Host', req.headers.host);
      proxyReq.setHeader('X-Requested-With', 'XMLHttpRequest');
    },
    onProxyRes: (proxyRes, req, res) => {
      // If auth responds with HTML, surface a hint in the dev server logs
      const ct = proxyRes.headers['content-type'] || '';
      if (req.url.startsWith('/api/auth/token') && typeof ct === 'string' && ct.includes('text/html')) {
        // eslint-disable-next-line no-console
        console.warn('[proxy] /api/auth/token responded with HTML content-type:', ct);
      }
    },
  };

  // API requests
  app.use('/api', createProxyMiddleware(commonProxyOptions));

  // Media files served by Django (e.g., profile images)
  app.use('/media', createProxyMiddleware(commonProxyOptions));
};
