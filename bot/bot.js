const { getBrowser } = require("./browserPool");
const WebSocket = require("ws");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();
  const page = await browser.newPage();

  console.log(`[${meeting_id}] Opening meeting:`, meeting_url);
  await page.goto(meeting_url, { waitUntil: "networkidle2" });
  await delay(8000);

  // 1️⃣ Set bot name
  try {
    await page.waitForSelector('input[name="displayName"]', { timeout: 5000 });
    await page.type('input[name="displayName"]', bot_name || "AI Assistant");
  } catch {
    console.log(`[${meeting_id}] Name input not found`);
  }

  // 2️⃣ Mute mic & camera
  await page.evaluate(() => {
    document.querySelector('[aria-label*="microphone"]')?.click();
    document.querySelector('[aria-label*="camera"]')?.click();
  });

  await delay(3000);

  // 3️⃣ Click Join
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
    console.log(`[${meeting_id}] ❌ Join button not found`);
    return;
  }

  console.log(`[${meeting_id}] ✅ Bot joined meeting`);
  await delay(5000); // allow WebRTC graph to stabilize

  // ================================
  // AUDIO CAPTURE STARTS HERE
  // ================================

  // 4️⃣ WebSocket to backend
  const socket = new WebSocket(
    `ws://localhost:8000/ws/audio/${meeting_id}`
  );

  socket.onopen = () => {
    console.log(`[${meeting_id}] 🔊 Audio WebSocket connected`);
  };

  // 5️⃣ Expose Node function to browser
  await page.exposeFunction("sendPCM", chunk => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(Buffer.from(chunk.buffer));
    }
  });

  // 6️⃣ Inject AudioWorklet & capture PCM
  await page.evaluate(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const audioCtx = new AudioContext({ sampleRate: 16000 });
    await audioCtx.audioWorklet.addModule("http://localhost:8000/static/audioWorklet.js");

    const source = audioCtx.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");

    worklet.port.onmessage = e => {
      window.sendPCM(e.data);
    };

    source.connect(worklet);
  });

  console.log(`[${meeting_id}] 🎙 PCM audio streaming started`);
}

// ENTRY POINT
try {
  const payload = JSON.parse(process.argv[2]);

  if (!payload.meeting_url || !payload.meeting_id) {
    throw new Error("Invalid payload");
  }

  joinMeeting(payload);
} catch (err) {
  console.error("❌ Invalid input:", err.message);
  process.exit(1);
}
