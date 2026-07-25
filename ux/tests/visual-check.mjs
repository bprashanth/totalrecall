import { chromium } from "playwright";

const base = process.env.FIELDNOTE_URL || "http://127.0.0.1:7300";
const output = process.env.FIELDNOTE_SCREENSHOTS || "/tmp/fieldnote-screens";
const browser = await chromium.launch({ headless: true });
const errors = [];

async function open(viewport, name) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`${name}: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`${name}: ${error.message}`));
  await page.goto(base, { waitUntil: "networkidle" });
  await page.screenshot({ path: `${output}/${name}-opening.png`, fullPage: false });
  await page.locator("#landscape").scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  await page.screenshot({ path: `${output}/${name}-landscape.png`, fullPage: false });
  await page.locator("#methods").scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  await page.screenshot({ path: `${output}/${name}-methods.png`, fullPage: false });
  await page.close();
}

await open({ width: 1440, height: 1000 }, "desktop");
await open({ width: 390, height: 844 }, "mobile");

if (process.env.FIELDNOTE_LIVE === "1") {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  page.on("pageerror", (error) => errors.push(`live: ${error.message}`));
  await page.goto(base, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Take a guided first look" }).click();
  await page.locator("#new-finding").waitFor({ timeout: 240_000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${output}/desktop-live-finding.png`, fullPage: false });
  await page.close();
}

if (process.env.FIELDNOTE_PAPER === "1") {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  page.on("pageerror", (error) => errors.push(`paper: ${error.message}`));
  await page.goto(`${base}/#methods`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Try an assisted natural regeneration example/i }).click();
  const draw = page.getByRole("button", { name: /Draw the first-look analogue in R/i });
  await draw.waitFor({ timeout: 240_000 });
  await draw.click();
  await page.locator(".r-plot svg").waitFor({ timeout: 60_000 });
  await page.locator(".method-result").scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${output}/desktop-paper-method.png`, fullPage: false });
  await page.close();
}

await browser.close();

if (errors.length) {
  throw new Error(`Browser errors:\n${errors.join("\n")}`);
}

console.log(`Saved Fieldnote screenshots in ${output}`);
