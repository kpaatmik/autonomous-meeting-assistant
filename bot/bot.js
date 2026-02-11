const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();
  const page = await browser.newPage();

  console.log(`[${meeting_id}] Opening meeting:`, meeting_url);
  await page.goto(meeting_url, { waitUntil: "networkidle2" });
  await delay(8000);

  // Set bot name
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

  // Click Join
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

  console.log(`[${meeting_id}] Bot joined meeting`);
  await delay(5000); // allow Jitsi to stabilize

  // ================================
  // AUDIO CAPTURE (JITSI NATIVE)
  // ================================

  const socket = new WebSocket(
    `ws://127.0.0.1:8000/ws/audio/${meeting_id}`
  );

  socket.onopen = async () => {
  console.log(`[${meeting_id}] 🔊 Audio WebSocket connected`);

  try {
    await delay(3000);

    const success = await page.evaluate(async () => {
      // Allow Jitsi to fully attach audio elements
      await new Promise(r => setTimeout(r, 3000));

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });

      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      await audioCtx.audioWorklet.addModule(
        "http://localhost:8000/static/audioWorklet.js"
      );

      const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");
      worklet.port.onmessage = e => window.sendPCM(e.data);

      const audioElements = Array.from(document.querySelectorAll("audio"));
      if (!audioElements.length) {
        console.warn("No Jitsi audio elements found yet");
        return false;
      }

      audioElements.forEach(audioEl => {
        try {
          const stream = audioEl.captureStream();
          const source = audioCtx.createMediaStreamSource(stream);
          source.connect(worklet);
        } catch (err) {
          console.warn("Failed to tap audio element:", err.message);
        }
      });

      return true;
    });

    if (success) {
      console.log(`[${meeting_id}] 🎙 PCM audio streaming started`);
    } else {
      console.warn(
        `[${meeting_id}] ⚠️ Audio not ready yet (no remote speakers)`
      );
      // DO NOT close socket — audio may appear later
    }
  } catch (err) {
    console.error(
      `[${meeting_id}] ❌ Audio capture setup failed:`,
      err.message
    );
  }
};


  socket.on("error", err => {
    console.error(`[${meeting_id}] WS error:`, err.message);
  });

  socket.on("close", code => {
    console.log(`[${meeting_id}] 🔌 WS closed`, code);
  });

  // Expose PCM sender
  await page.exposeFunction("sendPCM", chunk => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(Buffer.from(chunk.buffer));
    }
  });
}

// ENTRY POINT
try {
  const payload = JSON.parse(process.argv[2]);

  if (!payload.meeting_url || !payload.meeting_id) {
    throw new Error("Invalid payload");
  }

  joinMeeting(payload).catch(err => {
    console.error(
      `[${payload.meeting_id}] ❌ joinMeeting crashed:`,
      err.message
    );
  });
} catch (err) {
  console.error("❌ Invalid input:", err.message);
  process.exit(1);
}
