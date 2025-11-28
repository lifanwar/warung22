import {
    makeWASocket,
    DisconnectReason,
    useMultiFileAuthState,
    Browsers,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore,
  } from '@whiskeysockets/baileys';
  
  import fs from 'fs';
  import express from 'express';
  import path from 'path';
  import pino from 'pino';
  import { fileURLToPath } from 'url';
  import { dirname } from 'path';
  import axios from 'axios';
  
  // Setup __dirname
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);
  
  // Config
  const API_URL = 'http://localhost:8000';
  const API_KEY = 'PujanggaTSDUU@2$$%!!!';
  const PORT = parseInt(process.env.PORT_WA || 3000);

  // Logger
  const logger = pino({ level: 'silent' });
  
  // Express server untuk QR
  const app = express();
  const server = app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
  
  let sock;
  
  // Get quoted text
  function getQuoted(msg) {
    const q = msg.message?.extendedTextMessage?.contextInfo?.quotedMessage;
    return q?.conversation || q?.extendedTextMessage?.text || q?.imageMessage?.caption || q?.videoMessage?.caption || null;
  }
  
  // Get message text
  function getText(msg) {
    const m = msg.message;
    return m?.conversation || m?.extendedTextMessage?.text || null;
  }
  
  // Call Menu API
  async function askAPI(question) {
    try {
      const res = await axios.post(`${API_URL}/ask`, { question }, {
        headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
        timeout: 50000
      });
      return res.data.answer;
    } catch (e) {
      console.error('❌ API Error:', e.message);
      return null;
    }
  }
  
  // Refresh Cache API
  async function refreshCache() {
    try {
      const res = await axios.post(`${API_URL}/refresh`, {}, {
        headers: { 'X-API-Key': API_KEY },
        timeout: 10000
      });
      return res.data;
    } catch (e) {
      console.error('❌ Refresh Error:', e.message);
      return null;
    }
  }
  
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
          setTimeout(() => connectToWhatsApp(), 3000);
        }
      } else if (connection === "open") {
        console.log("✅ Connection opened");
        console.log("📋 Commands: .m (reply to message) | .refresh (update menu cache)\n");
      }
    });
    
    sock.ev.on("creds.update", saveCreds);
    sock.ev.on("lid-mapping.update", (mapping) => {
      console.log("LID mapping updated:", mapping);
    });

    function jidToNumber(jid) {
      // Hapus suffix @s.whatsapp.net atau @g.us
      return jid.replace(/(@s\.whatsapp\.net|@g\.us)$/, "");
    }
    
    
    // ===== MESSAGE HANDLER =====
    sock.ev.on('messages.upsert', async ({ type, messages: msgs }) => {
      if (type !== "notify") return;
      
      for (const message of msgs) {
        if (!message.message) continue;

        if (!message.message) continue;

        const chatJid = message.key.remoteJid;
        const senderJid = message.key.participant || chatJid;

        // Log setiap pesan yang BUKAN fromMe, lalu skip proses selanjutnya
        if (!message.key.fromMe) {
          const text = getText(message);
          const senderPhone = jidToNumber(senderJid); // function dari atas
          console.log(`📩 Pesan MASUK dari ${senderPhone}: "${text}"`);
          continue;
        }
      
        // ------ Mulai handler untuk pesan fromMe saja ---------
        const text = getText(message);
        
        // ===== HANDLE .refresh COMMAND =====
        if (text?.toLowerCase() === '.r') {
          console.log('\n🔄 Refresh cache requested...');
          
          // Edit pesan .refresh jadi loading
          await sock.sendMessage(chatJid, {
            text: '⏳ Refreshing cache...',
            edit: message.key
          });
          
          // Call refresh API
          const result = await refreshCache();
          
          if (result) {
            await sock.sendMessage(chatJid, {
              text: `✅ *Cache Updated*\n\n📦 Categories: ${result.categories_count}\n🍽️ Items: ${result.items_count}\n\n${result.message}`,
              edit: message.key
            });
            console.log(`✅ Cache refreshed: ${result.categories_count} categories, ${result.items_count} items\n`);
          } else {
            await sock.sendMessage(chatJid, {
              text: '❌ Failed to refresh cache. Please try again.',
              edit: message.key
            });
            console.log('❌ Refresh failed\n');
          }
          
          continue;
        }
        
        // ===== HANDLE .m COMMAND =====
        if (text?.toLowerCase() !== '.m') continue;
        
        const quoted = getQuoted(message);
        
        if (!quoted) {
          // Edit pesan .m jadi warning
          await sock.sendMessage(chatJid, {
            text: '⚠️ Reply pesan customer dengan .m',
            edit: message.key
          });
          continue;
        }
        
        console.log(`\n📝 Question: "${quoted}"`);
        
        // Edit pesan .m jadi loading
        await sock.sendMessage(chatJid, {
          text: '⏳ Sedang mencari pesanan...',
          edit: message.key
        });
        
        // Call API
        const answer = await askAPI(quoted);
        
        // Edit pesan .m jadi jawaban final
        await sock.sendMessage(chatJid, {
          text: answer ? `🤖 *Warung22*\n\n${answer}` : '⚠️ Bot sedang maintenance. Silakan coba lagi nanti.',
          edit: message.key
        });
        
        console.log(answer ? '✅ Response sent\n' : '⚠️ API failed\n');
      }
    });
  }
  
  // Start bot
  connectToWhatsApp();
  
