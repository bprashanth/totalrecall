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

if (process.env.FIELDNOTE_OVERLAP === "1") {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`overlap: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`overlap: ${error.message}`));
  await page.goto(base, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Ask this landscape" }).click();
  await page
    .getByPlaceholder("Where is there evidence—and where is there only silence?")
    .fill("Give me the squares where elephant and leopard records overlap, and show them on a map.");
  await page.locator(".send-button").click();
  await page.locator(".result-layer-legend").waitFor({ timeout: 240_000 });
  await page.locator("#new-finding").scrollIntoViewIfNeeded();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${output}/desktop-overlap.png`, fullPage: false });
  const sameYear = page.getByRole("button", {
    name: /Show only the .* squares where both were recorded in the same year/i,
  });
  await sameYear.waitFor({ timeout: 30_000 });
  await sameYear.click();
  await page.getByText(/15 1\.1 km squares hold records of both Elephant and Leopard\./).waitFor({
    timeout: 120_000,
  });
  await page.locator("#new-finding").scrollIntoViewIfNeeded();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${output}/desktop-overlap-same-year.png`, fullPage: false });
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
