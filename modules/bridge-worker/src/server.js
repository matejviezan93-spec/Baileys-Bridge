const express = require('express');
const promClient = require('prom-client');

const app = express();
const port = process.env.PORT || 4000;

const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

let activeSessionCount = 0;

const messageCounter = new promClient.Counter({
  name: 'bridge_worker_message_total',
  help: 'Total number of processed messages by the worker',
  registers: [register],
});

const activeSessionsGauge = new promClient.Gauge({
  name: 'bridge_worker_active_sessions',
  help: 'Current number of active worker sessions',
  registers: [register],
  collect() {
    this.set(activeSessionCount);
  },
});

const uptimeGauge = new promClient.Gauge({
  name: 'bridge_worker_uptime_seconds',
  help: 'Worker uptime in seconds',
  registers: [register],
  collect() {
    const uptime = process.uptime();
    this.set(uptime);
  },
});

app.get('/healthz', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.send(await register.metrics());
});

// Expose simple hooks so other modules can report activity when needed.
app.post('/metrics/message', (_req, res) => {
  messageCounter.inc();
  res.status(202).json({ status: 'accepted' });
});

app.post('/metrics/session/:state', (req, res) => {
  const { state } = req.params;
  if (state === 'start') {
    activeSessionCount += 1;
  } else if (state === 'end' && activeSessionCount > 0) {
    activeSessionCount -= 1;
  }
  activeSessionsGauge.set(activeSessionCount);
  res.status(202).json({ activeSessions: activeSessionCount });
});

app.listen(port, () => {
  console.log(`Bridge worker listening on port ${port}`);
});

module.exports = {
  app,
  register,
  messageCounter,
  activeSessionsGauge,
};
