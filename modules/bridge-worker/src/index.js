const express = require('express');
const client = require('prom-client');

const app = express();
const register = new client.Registry();
client.collectDefaultMetrics({ register });

const messageCounter = new client.Counter({
  name: 'bridge_worker_messages_total',
  help: 'Total number of messages processed by the worker',
  registers: [register],
});

const activeSessions = new client.Gauge({
  name: 'bridge_worker_active_sessions',
  help: 'Number of active worker sessions',
  registers: [register],
});

let currentSessions = 0;

const simulateActivity = () => {
  messageCounter.inc();
  currentSessions = Math.max(0, currentSessions + (Math.random() > 0.5 ? 1 : -1));
  activeSessions.set(currentSessions);
};

setInterval(simulateActivity, 10000);

app.get('/healthz', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

const port = process.env.PORT || 8080;
app.listen(port, () => {
  console.log(`Bridge worker listening on port ${port}`);
});
