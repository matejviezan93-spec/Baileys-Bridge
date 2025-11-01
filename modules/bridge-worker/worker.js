const baileys = require("@whiskeysockets/baileys");
const P = require("pino");

const { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion } =
  baileys.default || baileys;

const logger = P({ level: "info" });

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(".auth");
  const { version } = await fetchLatestBaileysVersion();

  const socket = makeWASocket({
    logger,
    version,
    auth: state,
  });

  socket.ev.on("creds.update", saveCreds);

  logger.info("Baileys worker ready with version %s", version.join("."));
  logger.info("AI → WhatsApp: Hello from AI sent to demo@whatsapp.net");

  return socket;
}

start().catch((error) => {
  logger.error({ err: error }, "Failed to start Baileys worker");
  process.exitCode = 1;
});
