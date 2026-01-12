// bot.js
const { getBrowser } = require("./browserPool");

const delay = ms => new Promise(res => setTimeout(res, ms));

async function joinMeeting(meetingUrl) {
  const browser = await getBrowser();   // 🔁 reuse Chrome
  const page = await browser.newPage(); // ➕ new TAB

  console.log("Opening meeting:", meetingUrl);
  await page.goto(meetingUrl, { waitUntil: "networkidle2" });

  await delay(8000);

  // Enter name
  try {
    await page.waitForSelector('input[name="displayName"]', { timeout: 5000 });
    await page.type('input[name="displayName"]', "AI Assistant");
  } catch {}

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

  if (joined) {
    console.log("✅ Bot joined meeting");
  } else {
    console.log("⚠️ Join button not found");
  }
}

// Run
const meetingUrl = process.argv[2];
if (!meetingUrl) {
  console.log("Usage: node bot.js <MEETING_URL>");
  process.exit(1);
}

joinMeeting(meetingUrl);
