// 大图可读性回归：仅在 work/tests 下生成 fixture 与浏览器证据。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.argv[2] || 'playwright');
const python = process.argv[3] || 'python';
const root = path.resolve(__dirname, '..');
const parent = path.join(root, 'work', 'tests');
fs.mkdirSync(parent, { recursive: true });
const output = fs.mkdtempSync(path.join(parent, 'readability-'));
const generated = spawnSync(python, ['-X', 'utf8', path.join(__dirname, 'render_readability_fixture.py'), output], { encoding: 'utf8' });
assert.equal(generated.status, 0, generated.stderr);

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const checks = [], errors = [], requests = [];
  try {
    const page = await browser.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) requests.push(request.url()); });
    async function measure(label, canvasId, expectedNodes) {
      const metrics = await page.locator(canvasId).evaluate(canvas => {
        const svg = canvas.querySelector('svg');
        const nodes = [...svg.querySelectorAll('[data-node]')].filter(n => getComputedStyle(n).display !== 'none');
        const text = nodes[0]?.querySelector('text');
        const matrix = text?.getScreenCTM();
        const stage = canvas.closest('.stage');
        return { nodes: nodes.length, fontPixels: text ? parseFloat(getComputedStyle(text).fontSize) * Math.hypot(matrix.a, matrix.b) : null,
          graphWidth: svg.viewBox.baseVal.width, graphHeight: svg.viewBox.baseVal.height,
          stageHeight: stage.clientHeight, viewportHeight: innerHeight,
          pageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
      });
      checks.push({ label, expectedNodes, ...metrics });
    }
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(pathToFileURL(path.join(output, 'index.html')).href);
      await measure(`${width}-all-tree`, '#tree-canvas', 182);
      await page.selectOption('#section', 'vol-18');
      await measure(`${width}-volume-tree`, '#tree-canvas', 11);
      await page.click('#network');
      await measure(`${width}-volume-network`, '#network-canvas', 11);
      await page.screenshot({ path: path.join(output, `${width}-volume.png`) });
      await page.selectOption('#section', '');
      await page.selectOption('#thread', 'narrow');
      await measure(`${width}-thread-network`, '#network-canvas', 3);
      await page.screenshot({ path: path.join(output, `${width}-thread.png`) });
    }
    // 在断言前保存全部 RED 观测，便于区分缺陷与启动错误。
    fs.writeFileSync(path.join(output, 'measurements.json'), JSON.stringify({ checks, errors, requests }, null, 2));
    console.log(JSON.stringify({ output, checks }, null, 2));
    for (const check of checks) {
      assert(check.fontPixels >= 12, `${check.label}: 标题被缩为 ${check.fontPixels.toFixed(2)}px`);
      assert.equal(check.nodes, check.expectedNodes, `${check.label}: 筛选必须排除无关节点`);
      assert(!check.pageOverflow, `${check.label}: 页面不应横向溢出`);
      assert(check.stageHeight <= check.viewportHeight, `${check.label}: 大图滚动必须限制在画布区域`);
      if (check.label.includes('thread-network')) assert(check.graphWidth <= 1600 && check.graphHeight <= 1600, '少量跨集节点应紧凑重排');
    }
    await page.locator('#network-canvas [data-node="vol-18-e1"]').click();
    assert.match(await page.locator('#detail-title').innerText(), /第18集事件1/);
    const fontBefore = checks.at(-1).fontPixels;
    await page.click('#zoom-in');
    await measure('zoom', '#network-canvas', 3);
    assert(checks.at(-1).fontPixels > fontBefore * 1.2, '缩放应改变实际文字大小');
    await page.selectOption('#section', 'vol-02');
    assert.equal(await page.locator('#network-canvas [data-node]:visible').count(), 0);
    assert(await page.locator('#empty-state').isVisible(), '空交集应有明确提示');
    await page.selectOption('#section', 'vol-18');
    assert.equal(await page.locator('#network-canvas [data-node]:visible').count(), 1);
    await page.locator('#network-canvas [data-node]:visible').press('Enter');
    assert.match(await page.locator('#detail-title').innerText(), /第18集事件1/);
    await page.selectOption('#thread', '__none');
    assert.equal(await page.locator('#network-canvas .relation:visible').count(), 0);
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    fs.writeFileSync(path.join(output, 'passed.json'), JSON.stringify({ passed: true, checks, errors, requests }, null, 2));
    console.log('Readability browser checks passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
