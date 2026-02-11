const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();
  const page = await browser.newPage();

  // ============================================
  // 🔥 BULLETPROOF INJECTION METHOD (NO LOG MESS)
  // ============================================

  await page.evaluateOnNewDocument(() => {
    const originalError = console.error;

    console.log = () => {};
    console.debug = () => {};
    console.info = () => {};
    console.warn = () => {};
    console.error = originalError;

    // Disable Jitsi debug mode
    window.localStorage.setItem("debug", "");
  });

  // Only show real browser errors
  page.on("pageerror", err => {
    console.error(`[BROWSER ERROR] ${err.message}`);
  });

  console.log(`[${meeting_id}] Opening meeting`);
  await page.goto(meeting_url, { waitUntil: "networkidle2" });
  await delay(8000);

  // ============================================
  // SET BOT NAME
  // ============================================

  try {
    await page.waitForSelector('input[name="displayName"]', { timeout: 5000 });
    await page.type('input[name="displayName"]', bot_name || "AI Assistant");
  } catch {
    console.log(`[${meeting_id}] Name input not found`);
  }

  // Mute mic & camera
  await page.evaluate(() => {
    document.querySelector('[aria-label*="microphone"]')?.click();
    document.querySelector('[aria-label*="camera"]')?.click();
  });

  await delay(3000);

  // ============================================
  // CLICK JOIN
  // ============================================

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
  // 🔊 AUDIO + WEBSOCKET
  // ============================================

  console.log(`[${meeting_id}] Connecting audio socket...`);

  const socket = new WebSocket(
    `ws://127.0.0.1:8000/ws/audio/${meeting_id}`
  );

  await page.exposeFunction("sendPCM", chunk => {
    try {
      if (!chunk || chunk.length === 0) return;
      if (socket.readyState !== WebSocket.OPEN) return;

      // chunk comes as plain object from page context
      // Convert it to a proper typed array
      let buffer;
      
      if (chunk instanceof ArrayBuffer) {
        buffer = Buffer.from(chunk);
      } else if (typeof chunk === "object" && chunk.length) {
        // Convert plain object/array to Int16Array then Buffer
        const int16 = new Int16Array(Object.values(chunk));
        buffer = Buffer.from(int16.buffer);
      } else if (Array.isArray(chunk)) {
        const int16 = new Int16Array(chunk);
        buffer = Buffer.from(int16.buffer);
      } else {
        console.warn("[PCM] Unknown data type:", typeof chunk, "keys:", Object.keys(chunk || {}));
        return;
      }

      console.log(`[${meeting_id}] ➡ Sending PCM: ${buffer.length} bytes`);
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
          console.log("[AudioWorklet] Module loaded");
        } catch (err) {
          console.error("[AudioWorklet] Load failed:", err.message);
          return false;
        }

        const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");

        worklet.port.onmessage = e => {
          // Convert Int16Array to plain array for crossing context boundary
          const arrayData = Array.from(e.data);
          console.log(`[AudioWorklet] Sending: ${arrayData.length} samples`);
          window.sendPCM(arrayData);
        };

        function attachAudioElement(audioEl) {
          try {
            const stream = audioEl.captureStream
              ? audioEl.captureStream()
              : audioEl.mozCaptureStream();

            const source = audioCtx.createMediaStreamSource(stream);
            source.connect(worklet);
            worklet.connect(audioCtx.destination);
            console.log("[Audio] Element attached");
            return true;
          } catch (err) {
            console.warn("[Audio] Attach failed:", err.message);
            return false;
          }
        }

        // Attach existing audio
        let count = 0;
        document.querySelectorAll("audio").forEach(el => {
          if (attachAudioElement(el)) count++;
        });

        return count > 0;
      });

      if (setupSuccess) {
        console.log(`[${meeting_id}] 🎙 PCM streaming active`);
      } else {
        console.warn(`[${meeting_id}] No audio elements found yet`);
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
// ENTRY POINT
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
