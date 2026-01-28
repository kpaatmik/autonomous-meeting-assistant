// browserPool.js
const puppeteer = require("puppeteer");

let browser = null;

async function getBrowser() {
  if (!browser) {
    console.log("🚀 Launching shared Chrome browser...");
    browser = await puppeteer.launch({
      headless: true, // production mode
      args: [
        "--use-fake-ui-for-media-stream",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--autoplay-policy=no-user-gesture-required"
      ]
    });
  }
  return browser;
}

module.exports = { getBrowser };
