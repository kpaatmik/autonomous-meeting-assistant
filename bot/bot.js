const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");
const { createClient } = require("redis"); // ✅ ADDED

const delay = ms => new Promise(res => setTimeout(res, ms));


// ============================================
// ✅ ADDED: CHAT SEND FUNCTION
// ============================================
async function sendMessage(page, message, meetingId) {
  try {
    // Try to find and click chat button
    const chatButton = await page.$('button[aria-label="Open chat"]') ||
                       await page.$('button[aria-label="Chat"]') ||
                       await page.$('[data-testid="chat-button"]') ||
                       await page.$('button[class*="chat"]') ||
                       await page.$('div[aria-label*="chat" i]');
    
    if (chatButton) {
      console.log(`[${meetingId}] Found chat button, clicking...`);
      await chatButton.click();
      await delay(1000); // Wait longer for chat to open
    } else {
      console.log(`[${meetingId}] Chat button not found, assuming chat is already open`);
    // More robust selector for Jitsi chat input - try multiple approaches
    let chatInput = null;

    // Try specific Jitsi selectors first (based on debug output)
    chatInput = await page.$('textarea[id="chat-input-messagebox"]') ||
                await page.$('textarea[id="usermsg"]') ||
                await page.$('input[id="usermsg"]') ||
                await page.$('textarea[placeholder*="message" i]') ||
                await page.$('input[placeholder*="message" i]') ||
                await page.$('textarea') ||
                await page.$('input[type="text"]') ||
                await page.$('div[contenteditable="true"][role="textbox"]') ||
                await page.$('div[contenteditable="true"]');

    if (!chatInput) {
      console.warn(`[${meetingId}] Chat input not found with standard selectors, trying broader search...`);

      // Try to find any visible input-like element in chat area
      chatInput = await page.evaluateHandle(() => {
        // Look for elements that might be chat inputs
        const candidates = [
          ...document.querySelectorAll('textarea'),
          ...document.querySelectorAll('input[type="text"]'),
          ...document.querySelectorAll('div[contenteditable="true"]')
        ].filter(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 50 && rect.height > 20 && rect.top > 0;
        });

        // Prefer elements that are currently visible and in a chat-like context
        for (const el of candidates) {
          if (el.closest('[class*="chat"]') || el.closest('[id*="chat"]') ||
              el.getAttribute('placeholder')?.toLowerCase().includes('message') ||
              el.getAttribute('aria-label')?.toLowerCase().includes('message') ||
              el.id === 'chat-input-messagebox') {
            return el;
          }
        }

        // Fallback to first visible candidate
        return candidates[0] || null;
      });
    }

    if (!chatInput) {
      console.warn(`[${meetingId}] Chat input not found on page`);
      return;
    }

    console.log(`[${meetingId}] Found chat input, sending message...`);

    // Focus and type
    await chatInput.click();
    await delay(300);
    await page.keyboard.type(message);
    await delay(200);

    // Try to send - look for send button or press enter
    const sendButton = await page.$('button[aria-label="Send message"]') ||
                       await page.$('button[type="submit"]') ||
                       await page.$('button[class*="send"]') ||
                       await page.$('[data-testid="chat-send-button"]');

    if (sendButton) {
      console.log(`[${meetingId}] Found send button, clicking...`);
      await sendButton.click();
    } else {
      console.log(`[${meetingId}] Send button not found, pressing Enter...`);
      await page.keyboard.press("Enter");
    }

    console.log(`[${meetingId}] Message sent: ${message.substring(0, 50)}...`);

  } catch (err) {
    console.error(`[${meetingId}] Chat send error: ${err.message}`);
  }
}


// ============================================
// ✅ ADDED: REDIS LISTENER
// ============================================
async function listenForAnswers(page, meetingId) {
  let redis = null;
  let lastId = "$";
  let errorCount = 0;
  const MAX_ERRORS = 5;

  const connect = async () => {
    try {
      redis = createClient();
      await redis.connect();
      console.log(`[${meetingId}] Redis connected, listening for answers...`);
      errorCount = 0;
    } catch (err) {
      console.error(`[${meetingId}] Redis connect failed: ${err.message}`);
      setTimeout(connect, 3000);
    }
  };

  await connect();

  while (true) {
    try {
      if (!redis) {
        await delay(1000);
        await connect();
        continue;
      }

      const response = await redis.xRead(
        [{ key: `meeting:${meetingId}:answers`, id: lastId }],
        { BLOCK: 2000 }
      );

      if (response && response.length > 0) {
        for (const stream of response) {
          for (const msg of stream.messages) {
            const data = msg.message;
            const answer = data.response;

            if (answer && answer.trim().length > 0) {
              console.log(`[${meetingId}] New answer received, sending to chat...`);
              const question = data.question || "Question";
              const formattedMessage = `🤖 AI Assistant\n\n❓ ${question}\n\n💡 ${answer}`;
              await sendMessage(page, formattedMessage, meetingId);
              await delay(500);
            }

            lastId = msg.id;
          }
        }
      }
      errorCount = 0;

    } catch (err) {
      errorCount++;
      if (errorCount > MAX_ERRORS) {
        console.error(`[${meetingId}] Too many Redis errors, reconnecting...`);
        try {
          await redis?.quit();
        } catch (e) {}
        redis = null;
        lastId = "$";
        errorCount = 0;
        await delay(2000);
        await connect();
      } else {
        console.warn(`[${meetingId}] Redis read error (${errorCount}/${MAX_ERRORS}): ${err.message}`);
        await delay(1000);
      }
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
    // Try multiple selectors for name input
    const nameInput = await page.$('input[name="displayName"]') ||
                      await page.$('input[id="displayName"]') ||
                      await page.$('input[placeholder*="name" i]') ||
                      await page.$('input[type="text"]');

    if (nameInput) {
      await nameInput.clear();
      await nameInput.type(bot_name || "AI Assistant");
      console.log(`[${meeting_id}] Name input found and set`);
    } else {
      console.log(`[${meeting_id}] Name input not found - may already be set`);
    }
  } catch (err) {
    console.log(`[${meeting_id}] Name input error: ${err.message}`);
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
  // ✅ START LISTENING AFTER FULL JOIN (ADDED)
  // ============================================
  // Wait additional time to ensure name input is gone and meeting is fully loaded
  setTimeout(async () => {
    console.log(`[${meeting_id}] Starting Redis listener after full join...`);
    listenForAnswers(page, meeting_id).catch(err => {
      console.error(`[${meeting_id}] Listener error: ${err.message}`);
    });
  }, 10000); // 10 second delay to ensure full join


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

    try {
      await delay(3000);

      const setupSuccess = await page.evaluate(async () => {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const audioCtx = new AudioCtx({ sampleRate: 16000 });

        if (audioCtx.state === "suspended") {
          await audioCtx.resume();
        }

        try {
          await audioCtx.audioWorklet.addModule(
            "http://localhost:8000/static/audioWorklet.js"
          );
        } catch (err) {
          console.error("[AudioWorklet] Load failed:", err.message);
          return false;
        }

        const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");
        worklet.connect(audioCtx.destination);

        worklet.port.onmessage = e => {
          const arrayData = Array.from(e.data);
          window.sendPCM(arrayData);
        };

        const attached = new WeakSet();

        function attachAudioElement(el) {
          if (attached.has(el)) return false;
          try {
            const stream = el.captureStream ? el.captureStream() : el.mozCaptureStream();
            const source = audioCtx.createMediaStreamSource(stream);
            source.connect(worklet);
            attached.add(el);
            return true;
          } catch (err) {
            return false;
          }
        }

        let count = 0;
        document.querySelectorAll("audio, video").forEach(el => {
          if (attachAudioElement(el)) count++;
        });

        const observer = new MutationObserver(() => {
          document.querySelectorAll("audio, video").forEach(el => {
            attachAudioElement(el);
          });
        });

        observer.observe(document.body, {
          childList: true,
          subtree: true
        });

        setInterval(() => {
          document.querySelectorAll("audio, video").forEach(el => {
            attachAudioElement(el);
          });
        }, 3000);

        return count > 0;
      });

      if (setupSuccess) {
        console.log(`[${meeting_id}] 🎙 PCM streaming active`);
      } else {
        console.warn(`[${meeting_id}] No audio elements found yet, will retry`);
      }
    } catch (err) {
      console.error(`[${meeting_id}] Audio setup error: ${err.message}`);
    }
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