/* node --test test/x-pixel.test.mjs — X Pixelが成功登録だけを計測する配線を確認する */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import worker from '../_worker.js';

const index = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const privacy = await readFile(new URL('../privacy.html', import.meta.url), 'utf8');
const workerSource = await readFile(new URL('../_worker.js', import.meta.url), 'utf8');

for (const [name, html] of [['index', index], ['privacy', privacy]]) {
  assert.match(html, /static\.ads-twitter\.com\/uwt\.js/, `${name}: base script`);
  assert.match(html, /twq\('config','rembf'\)/, `${name}: pixel config`);
}

assert.match(index, /twq\('event', 'tw-rembf-repin'/, 'Lead event ID');
assert.match(index, /status: 'completed'/, 'completed status');
assert.match(index, /conversion_id: result\.data\.conversion_id/, 'deduplication ID');
assert.doesNotMatch(index, /twq\('event'[\s\S]{0,300}email/i, 'email must not be sent to X');

assert.match(workerSource, /const conversionId = crypto\.randomUUID\(\)/, 'registration ID');
assert.match(workerSource, /json\(\{ ok: true, conversion_id: conversionId \}\)/, 'registration response');

const writes = [];
const env = {
  DB: {
    prepare(sql) {
      return {
        bind(...args) {
          writes.push({ sql, args });
          return { run: async () => ({ success: true }) };
        },
      };
    },
  },
};
const response = await worker.fetch(
  new Request('https://ainorigohan.com/api/register', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email: 'pixel-test@example.com', area: '渋谷|x/test' }),
  }),
  env,
  { waitUntil() {} }
);
const payload = await response.json();
assert.equal(response.status, 200);
assert.equal(payload.ok, true);
assert.match(payload.conversion_id, /^[0-9a-f-]{36}$/i);
assert.equal(writes.length, 1);
assert.equal(writes[0].args[0], payload.conversion_id, 'D1 ID and X conversion ID must match');

console.log('ok');
