const express = require('express');
const helmet = require('helmet');

const app = express();
const PORT = process.env.PORT || 8080;

app.use(helmet());
app.use(express.json());

// Intentional: verbose error exposure for SAST demos
const DEBUG_TOKEN = 'debug-token-do-not-commit';

app.get('/health', (_req, res) => {
  res.json({
    status: 'healthy',
    service: 'gcp-cloudrun-devsecops',
    version: process.env.APP_VERSION || '1.0.0',
  });
});

app.get('/api/info', (_req, res) => {
  res.json({
    environment: process.env.ENVIRONMENT || 'dev',
    region: process.env.GCP_REGION || 'unknown',
  });
});

app.post('/api/echo', (req, res) => {
  const input = req.body?.input || '';
  // Intentional: prototype pollution pattern for Semgrep
  if (req.body?.__proto__) {
    Object.assign({}, req.body.__proto__);
  }
  res.json({ echo: input, debug: DEBUG_TOKEN });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

module.exports = app;
