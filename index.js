// index.js
import {
  makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  Browsers,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  isPnUser,
  isJidGroup
} from '@whiskeysockets/baileys';

import fs from 'fs';
import express from 'express';
import path from 'path';
import pino from 'pino';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// import helpers
import { 
  isPrivateChat,        
  getSenderIdentifier,  
  getPreferredJid,      
  extractLocation       
} from './utils/whatsappHelpers.js';

// handlers
import { handleLocationMessage } from './handlers/locationHandler.js';
import { handleTextCommand } from './handlers/commandHandler.js';
import { handleCoordinateMessage, parseCoordinates } from './handlers/coordinateHandler.js'; 

// Setup __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Logger
const logger = pino({ level: 'silent' });

// Express server untuk QR
const app = express();
const PORT = parseInt(process.env.PORT);
const server = app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

let sock;

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("session1");
  
  const { version, isLatest } = await fetchLatestBaileysVersion();
  console.log(`Using WA v${version.join(".")}, latest: ${isLatest}`);
  
  sock = makeWASocket({
    printQRInTerminal: false,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    version,
    browser: Browsers.macOS("Desktop"),
    logger: logger,
    getMessage: async (key) => undefined
  });
  
  // Connection handler
  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;
    
    if (qr) {
      let htmlTemplate = fs.readFileSync(path.join(__dirname, 'src', 'index.html'), 'utf8');
      htmlTemplate = htmlTemplate.replace('{{QR_CODE_PLACEHOLDER}}',
        `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(qr)}&size=300x300`);
      htmlTemplate = htmlTemplate.replace('{{CURRENT_YEAR}}', new Date().getFullYear());
      
      app.get("/", (req, res) => res.send(htmlTemplate));
    }
    
    if (connection === "close") {
      server.close();
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log("Connection closed, reconnecting:", shouldReconnect);
      
      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === "open") {
      console.log("Connection opened");
    }
  });
  
  sock.ev.on("creds.update", saveCreds);
  sock.ev.on("lid-mapping.update", (mapping) => {
    console.log("LID mapping updated:", mapping);
  });
  
  // ===== MESSAGE HANDLER =====
  sock.ev.on('messages.upsert', async ({ type, messages: msgs }) => {
    if (type !== "notify") return;
    
    for (const message of msgs) {
      if (!message.message) continue;
      if (message.key.fromMe) continue;
      
      const chatJid = message.key.remoteJid;
      const chatJidAlt = message.key.remoteJidAlt;
      
      const isGroup = isJidGroup(chatJid);
      const isPrivate = isPrivateChat(chatJid);
      
      // Hanya handle private chat
      if (!isPrivate) continue;
      
      const sender = getSenderIdentifier(chatJid, chatJidAlt);
      const preferredJid = getPreferredJid(chatJid, chatJidAlt);
      
      // Extract location
      const location = extractLocation(message);
      
      // ===== HANDLE LOCATION (AUTO SEARCH) =====
      if (location) {
        await handleLocationMessage(sock, sender, preferredJid, location);
        continue;
      }
      
      // ===== HANDLE TEXT COMMANDS =====
      const messageContent = 
        message.message.conversation || 
        message.message.extendedTextMessage?.text || 
        '';

      const text = messageContent.trim();
      
      if (text) {
        await handleTextCommand(sock, preferredJid, text, message);
        
        const coordinates = parseCoordinates(text);
        if (coordinates) {
          // ===== HANDLE COORDINATE =====
          await handleCoordinateMessage(sock, sender, preferredJid, coordinates);
          continue;
        }
        
      }

    }
  });

}

// Start bot
connectToWhatsApp();
