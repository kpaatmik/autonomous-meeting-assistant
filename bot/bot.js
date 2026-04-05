const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");
const { createClient } = require("redis"); // ✅ ADDED

const delay = ms => new Promise(res => setTimeout(res, ms));


// ============================================
// ✅ ADDED: CHAT SEND FUNCTION
// ============================================
async function sendMessage(page, message) {
  try {
    const chatButton = await page.$('button[aria-label="Open chat"]');
    if (chatButton) {
      await chatButton.click();
      await page.waitForTimeout(500);
    }

    const chatInput = await page.waitForSelector(
  'textarea, div[contenteditable="true"]',
  { timeout: 5000 }
    );

    await chatInput.focus();
    await page.keyboard.type(message);
    await page.keyboard.press("Enter");

    console.log("[BOT] Message sent:", message);

  } catch (err) {
    console.error("[BOT] Chat send error:", err.message);
  }
}


// ============================================
// ✅ ADDED: REDIS LISTENER
// ============================================
async function listenForAnswers(page, meetingId) {
  const redis = createClient();

  await redis.connect();

  let lastId = "0";

  console.log(`[${meetingId}] Listening for LLM answers...`);

  while (true) {
    try {
      const response = await redis.xRead(
        [{ key: `meeting:${meetingId}:answers`, id: lastId }],
        { BLOCK: 1000 }
      );

      if (response) {
        for (const stream of response) {
          for (const message of stream.messages) {
            const data = message.message;

            const answer = data.response;

            if (answer && answer.length > 0) {
              await sendMessage(page, `AI: ${answer}`);
            }

            lastId = message.id;
          }
        }
      }
    } catch (err) {
      console.error(`[${meetingId}] Redis read error: ${err.message}`);
      await delay(1000);
    }
  }
}


// ============================================
// ORIGINAL CODE (UNCHANGED)
// ============================================

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();
  const page = await browser.newPage();

  await page.evaluateOnNewDocument(() => {
    const originalError = console.error;

    console.log = () => {};
    console.debug = () => {};
    console.info = () => {};
    console.warn = () => {};
    console.error = originalError;

    window.localStorage.setItem("debug", "");
  });

  page.on("pageerror", err => {
    console.error(`[BROWSER ERROR] ${err.message}`);
  });

  console.log(`[${meeting_id}] Opening meeting`);
  await page.goto(meeting_url, { waitUntil: "networkidle2" });
  await delay(8000);

  try {
    await page.waitForSelector('input[name="displayName"]', { timeout: 5000 });
    await page.type('input[name="displayName"]', bot_name || "AI Assistant");
  } catch {
    console.log(`[${meeting_id}] Name input not found`);
  }

  await page.evaluate(() => {
    document.querySelector('[aria-label*="microphone"]')?.click();
    document.querySelector('[aria-label*="camera"]')?.click();
  });

  await delay(3000);

  const joined = await page.evaluate(() => {
    const btn =
      document.querySelector('[data-testid="prejoin.joinMeeting"]') ||
      [...document.querySelectorAll("button")].find(b =>
        b.innerText.toLowerCase().includes("join")
      );

    if (btn) {
      btn.click();
      return true;
    }
    return false;
  });

  if (!joined) {
    console.log(`[${meeting_id}] Join button not found`);
    return;
  }

  console.log(`[${meeting_id}] Bot joined`);
  await delay(5000);


  // ============================================
  // ✅ START LISTENING AFTER JOIN (ADDED)
  // ============================================
  setTimeout(() => {
  listenForAnswers(page, meeting_id);
    }, 0);


  console.log(`[${meeting_id}] Connecting audio socket...`);

  const socket = new WebSocket(
    `ws://127.0.0.1:8000/ws/audio/${meeting_id}`
  );

  await page.exposeFunction("sendPCM", chunk => {
    try {
      if (!chunk || chunk.length === 0) return;
      if (socket.readyState !== WebSocket.OPEN) return;

      let buffer;

      if (chunk instanceof ArrayBuffer) {
        buffer = Buffer.from(chunk);
      } else if (typeof chunk === "object" && chunk.length) {
        const int16 = new Int16Array(Object.values(chunk));
        buffer = Buffer.from(int16.buffer);
      } else if (Array.isArray(chunk)) {
        const int16 = new Int16Array(chunk);
        buffer = Buffer.from(int16.buffer);
      } else {
        console.warn("[PCM] Unknown data type:", typeof chunk, "keys:", Object.keys(chunk || {}));
        return;
      }

      socket.send(buffer);

    } catch (err) {
      console.error(`[${meeting_id}] sendPCM error: ${err.message}`);
    }
  });

  socket.on("open", async () => {
    console.log(`[${meeting_id}] 🔊 Audio socket connected`);
    // (unchanged rest)
  });

  socket.on("error", err => {
    console.error(`[${meeting_id}] WS ERROR: ${err.message}`);
  });

  socket.on("close", code => {
    console.log(`[${meeting_id}] WS closed (${code})`);
  });
}


// ============================================
// ENTRY POINT (UNCHANGED)
// ============================================

try {
  const payload = JSON.parse(process.argv[2]);

  if (!payload.meeting_url || !payload.meeting_id) {
    throw new Error("Invalid payload");
  }

  joinMeeting(payload).catch(err => {
    console.error(
      `[${payload.meeting_id}] joinMeeting crashed: ${err.message}`
    );
  });

} catch (err) {
  console.error("Invalid input:", err.message);
  process.exit(1);
}