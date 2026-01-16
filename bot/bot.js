// bot/bot.js
const { getBrowser } = require("./browserPool");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting({ meeting_id, meeting_url, bot_name }) {
  const browser = await getBrowser();     //  Shared browser
  const page = await browser.newPage();   //  Isolated tab per meeting

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

  // Mute mic & camera BEFORE join
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

  if (joined) {
    console.log(`[${meeting_id}]  Bot joined meeting`);
  } else {
    console.log(`[${meeting_id}]  Join button not found`);
  }

  /*
   FUTURE (DO NOT IMPLEMENT NOW)
   ───────────────────────────
   - Inject AudioWorklet
   - Capture PCM audio
   - Stream to backend WebSocket
   - Receive TTS audio back
  */
}

//  ENTRY POINT
try {
  const payload = JSON.parse(process.argv[2]);

  if (!payload.meeting_url || !payload.meeting_id) {
    throw new Error("Invalid payload");
  }

  joinMeeting(payload);
} catch (err) {
  console.error("❌ Invalid input:", err.message);
  console.log("Usage: node bot.js '<JSON_PAYLOAD>'");
  process.exit(1);
}
