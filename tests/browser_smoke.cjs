// 可选浏览器验收：Playwright 仅用于开发验证，产品运行不依赖它。
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.argv[2] || 'playwright');

(async () => {
  const output = path.resolve(process.argv[3] || 'work/demo/views');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [], external = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (/^https?:/.test(r.url())) external.push(r.url()); });
    await page.goto(pathToFileURL(path.join(output, 'index.html')).href);
    assert.equal(await page.locator('#tree-canvas [data-node]').count(), 10);
    await page.locator('#tree-canvas [data-node="letter"]').click();
    assert.equal(await page.locator('#detail-title').innerText(), '信封的第二道折痕');
    await page.locator('#thread').selectOption('identity');
    assert.equal(await page.locator('#status').innerText(), '已回收');
    await page.locator('#network').click();
    assert.equal(await page.locator('#tree-canvas').isVisible(), false);
    assert.equal(await page.locator('#network-canvas').isVisible(), true);
    await page.locator('#section').selectOption('act1');
    assert.equal(await page.locator('#network-canvas [data-node="reveal"]').isVisible(), false);
    assert.equal(await page.locator('#network-canvas [data-node="letter"]').isVisible(), true);
    await page.locator('#section').selectOption('');
    const renderedFont = () => page.locator('#network-canvas [data-node="letter"] text').first().evaluate(el =>
      parseFloat(getComputedStyle(el).fontSize) * el.getScreenCTM().a);
    const beforeZoom = await renderedFont();
    await page.locator('#zoom-in').click();
    assert(Math.abs(await renderedFont() / beforeZoom - 1.25) < .01);
    await page.locator('#zoom-out').click();
    await page.screenshot({ path: path.join(output, 'network-preview.png'), fullPage: true });
    await page.locator('#tree').click();
    await page.locator('#thread').selectOption('');
    await page.screenshot({ path: path.join(output, 'tree-preview.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'mobile-preview.png'), fullPage: true });
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    fs.writeFileSync(path.join(output, 'browser-check.json'), JSON.stringify({ passed: true, nodeCount: 10, checks: ['node details', 'hidden thread', 'tree/network switch', 'section filter', 'zoom', '390px viewport'], scriptErrors: errors, externalRequests: external }, null, 2));
    console.log('Browser smoke passed: node details, hidden thread, network, section, zoom, offline requests.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
