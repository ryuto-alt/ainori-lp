#!/usr/bin/env node
/**
 * about.html の動きを、決まった時刻・決まったスクロール位置で撮る(headless Chrome + CDP、puppeteer なし)。
 *
 *   node test/about/shots.mjs <url> <出力の頭> --plan "<手順>;<手順>;..." [--w 390] [--h 844] [--dpr 2]
 *                             [--scheme light|dark] [--mobile] [--reduce] [--wait 1500]
 *
 * 手順:
 *   t:ms            ms 待って撮る
 *   y:px@ms         window.scrollTo(0, px) して ms 待って撮る
 *   sel:css+off@ms  css の要素の上端 + off px まで流して撮る(off は画面の高さに対する % にもできる: +50%)
 *   ctr:css+frac@ms 要素の高さの frac(0〜1, 既定 .5)の所を画面の真ん中に合わせて撮る
 *   m:x,y           マウスを動かすだけ(撮らない)
 *   c:x,y@ms        クリックして ms 待つ(撮らない)
 *   js:式           ページで式を評価して結果を表示(撮らない)
 * 例外とコンソールの warn/error は全部表示する。
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';

const CHROME = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const argv = process.argv.slice(2);
const arg = (n, d) => { const i = argv.indexOf('--' + n); return i === -1 ? d : argv[i + 1]; };
const has = (n) => argv.includes('--' + n);
const url = argv[0], prefix = argv[1];
const W = +arg('w', 390), H = +arg('h', 844), DPR = +arg('dpr', 2), WAIT = +arg('wait', 1500);
const plan = (arg('plan', 't:0')).split(';').map((s) => s.trim()).filter(Boolean);
const PORT = 9300 + Math.floor(Math.random() * 400);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'aboutshot-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile,
  '--window-size=' + W + ',' + H, '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--disable-background-timer-throttling', '--mute-audio',
  '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', 'about:blank',
], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (p) => new Promise((res, rej) => {
  http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => { let b = ''; r.on('data', (d) => (b += d)); r.on('end', () => { try { res(JSON.parse(b)); } catch (e) { rej(e); } }); }).on('error', rej);
});
class CDP {
  static async connect(u) {
    const ws = new WebSocket(u); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
    const c = new CDP(); c.ws = ws; c.id = 0; c.p = new Map();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && c.p.has(m.id)) { const q = c.p.get(m.id); c.p.delete(m.id); m.error ? q.j(new Error(JSON.stringify(m.error))) : q.r(m.result); return; }
      if (m.method === 'Runtime.consoleAPICalled' && /warn|error|log/.test(m.params.type)) {
        console.log('[%s] %s', m.params.type, m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' '));
      } else if (m.method === 'Runtime.exceptionThrown') {
        const d = m.params.exceptionDetails; console.log('[exception]', (d.exception && d.exception.description) || d.text);
      }
    };
    return c;
  }
  send(method, params = {}) { const id = ++this.id; this.ws.send(JSON.stringify({ id, method, params })); return new Promise((r, j) => this.p.set(id, { r, j })); }
}
const evaluate = async (cdp, expr) => (await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result.value;

(async () => {
  try {
    for (let i = 0; i < 80; i++) { try { await getJSON('/json/version'); break; } catch { await sleep(250); } }
    const page = (await getJSON('/json/list')).find((t) => t.type === 'page');
    const cdp = await CDP.connect(page.webSocketDebuggerUrl);
    await cdp.send('Page.enable'); await cdp.send('Runtime.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: DPR, mobile: has('mobile') });
    const feats = [];
    if (arg('scheme')) feats.push({ name: 'prefers-color-scheme', value: arg('scheme') });
    if (has('reduce')) feats.push({ name: 'prefers-reduced-motion', value: 'reduce' });
    if (feats.length) await cdp.send('Emulation.setEmulatedMedia', { features: feats });
    if (has('mobile')) await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
    await cdp.send('Page.navigate', { url });
    await sleep(300);
    let n = 0;
    const shot = async () => {
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
      const f = `${prefix}-${String(n++).padStart(2, '0')}.png`; fs.writeFileSync(f, Buffer.from(data, 'base64')); console.log('wrote', f);
    };
    for (const step of plan) {
      const [head, waitStr] = step.split('@');
      const wait = waitStr !== undefined ? +waitStr : WAIT;
      if (head.startsWith('t:')) { await sleep(+head.slice(2)); await shot(); }
      else if (head.startsWith('y:')) { await evaluate(cdp, `window.scrollTo(0, ${+head.slice(2)})`); await sleep(wait); await shot(); }
      else if (head.startsWith('sel:')) {
        const m = head.slice(4).match(/^(.*?)([+-]\d+%?)?$/);
        const sel = m[1], off = m[2] || '+0';
        const y = await evaluate(cdp, `(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return -1;
          const o = ${JSON.stringify(off)}; const v = o.endsWith('%') ? innerHeight * parseFloat(o) / 100 : parseFloat(o);
          const y = e.getBoundingClientRect().top + scrollY + v; scrollTo(0, y); return Math.round(y); })()`);
        console.log('scroll', sel, off, '->', y);
        await sleep(wait); await shot();
      } else if (head.startsWith('ctr:')) {
        const m = head.slice(4).match(/^(.*?)(\+[\d.]+)?$/);
        const sel = m[1], frac = m[2] ? parseFloat(m[2]) : .5;
        const y = await evaluate(cdp, `(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return -1;
          const r = e.getBoundingClientRect(); const y = r.top + scrollY + r.height * ${frac} - innerHeight / 2; scrollTo(0, y); return Math.round(y); })()`);
        console.log('center', sel, frac, '->', y);
        await sleep(wait); await shot();
      } else if (head.startsWith('m:')) {
        const [x, y] = head.slice(2).split(',').map(Number);
        await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none' }); await sleep(wait);
      } else if (head.startsWith('c:')) {
        const [x, y] = head.slice(2).split(',').map(Number);
        await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none' });
        await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
        await sleep(60);
        await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
        await sleep(wait);
      } else if (head.startsWith('js:')) {
        console.log('js =>', JSON.stringify(await evaluate(cdp, head.slice(3))));
      }
    }
  } catch (e) { console.error(e); process.exitCode = 1; }
  finally { chrome.kill(); setTimeout(() => { try { fs.rmSync(profile, { recursive: true, force: true }); } catch {} process.exit(); }, 400); }
})();
