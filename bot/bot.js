const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();
  const page = await browser.newPage();

  // 🔥 IMPORTANT: See browser console logs
  page.on("console", msg => {
    console.log(`[BROWSER] ${msg.text()}`);
  });

  page.on("pageerror", err => {
    console.error(`[BROWSER ERROR] ${err.message}`);
  });

  console.log(`[${meeting_id}] Opening meeting: ${meeting_url}`);
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
  await delay(5000);

  // ============================
  // 🔊 AUDIO + WEBSOCKET
  // ============================

  console.log(`[${meeting_id}] Attempting WebSocket connection...`);

  const socket = new WebSocket(
    `ws://127.0.0.1:8000/ws/audio/${meeting_id}`
  );

  // Expose sendPCM BEFORE page.evaluate uses it
  await page.exposeFunction("sendPCM", chunk => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(Buffer.from(chunk.buffer));
    }
  });

  socket.on("open", async () => {
    console.log(`[${meeting_id}] 🔊 Audio WebSocket connected`);

    try {
      await delay(3000);

      const success = await page.evaluate(async () => {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const audioCtx = new AudioCtx({ sampleRate: 16000 });

  if (audioCtx.state === "suspended") {
    await audioCtx.resume();
  }

  await audioCtx.audioWorklet.addModule(
    "http://127.0.0.1:8000/static/audioWorklet.js"
  );

  const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");

  let frameCount = 0;

  worklet.port.onmessage = e => {
    frameCount++;
    if (frameCount % 100 === 0) {
      console.log("PCM frames flowing:", frameCount);
    }
    window.sendPCM(e.data);
  };

  function attachAudioElement(audioEl) {
    try {
      const stream = audioEl.captureStream();
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(worklet);
      console.log("Attached to audio element");
    } catch (err) {
      console.warn("Attach failed:", err.message);
    }
  }

  // Attach existing audio elements
  document.querySelectorAll("audio").forEach(attachAudioElement);

  // 🔥 Observe future audio elements (THIS IS THE FIX)
  const observer = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.tagName === "AUDIO") {
          console.log("New audio element detected");
          attachAudioElement(node);
        }
      });
    });
  });

  observer.observe(document.body, { childList: true, subtree: true });

  return true;
});


      if (success) {
        console.log(`[${meeting_id}] 🎙 PCM audio streaming started`);
      } else {
        console.warn(`[${meeting_id}] ⚠️ No remote speakers yet`);
      }

    } catch (err) {
      console.error(`[${meeting_id}] ❌ Audio setup failed:`, err.message);
    }
  });

  socket.on("error", err => {
    console.error(`[${meeting_id}] ❌ WS ERROR:`, err.message);
  });

  socket.on("close", code => {
    console.log(`[${meeting_id}] 🔌 WS CLOSED:`, code);
  });
}

// ============================
// ENTRY POINT
// ============================

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
