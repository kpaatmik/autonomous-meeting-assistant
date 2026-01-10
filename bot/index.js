const puppeteer = require("puppeteer");

(async () => {
  const meetingUrl = process.argv[2];

  if (!meetingUrl) {
    console.log("Usage: node index.js <JITSI_MEETING_URL>");
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    headless: false, // keep visible for learning
    args: [
      "--use-fake-ui-for-media-stream",
      "--no-sandbox",
      "--disable-setuid-sandbox"
    ]
  });

  const page = await browser.newPage();
  await page.goto(meetingUrl, { waitUntil: "networkidle2" });

  // Wait for UI
  await new Promise(r => setTimeout(r, 8000));

  // Enter bot name
  await page.keyboard.type("AI Assistant");
  await new Promise(r => setTimeout(r, 1000));

  // Press Enter to join
  await page.keyboard.press("Enter");

  // Wait for meeting UI
  await new Promise(r => setTimeout(r, 6000));

  // Mute microphone
  await page.evaluate(() => {
    const micButton = document.querySelector('[aria-label*="microphone"]');
    if (micButton) micButton.click();
  });

  // Mute camera
  await page.evaluate(() => {
    const camButton = document.querySelector('[aria-label*="camera"]');
    if (camButton) camButton.click();
  });

  console.log("✅ Bot joined with mic & camera muted");

})();
