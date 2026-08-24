/* node test/mask-email.test.mjs — Discord通知でメアドが漏れないことだけ見る */
import assert from 'node:assert/strict';
import { maskEmail } from '../_worker.js';

for (const [input, want] of [
  ['ryuto@gmail.com', 'ry****@gmail.com'],
  ['a@b.jp', 'a****@b.jp'],
  ['ab@b.jp', 'ab****@b.jp'],
  ['very.long.name+tag@sub.example.co.jp', 've****@sub.example.co.jp'],
  ['not-an-email', 'not-an-email'], // 壊れた入力でも例外にしない
]) {
  assert.equal(maskEmail(input), want, input);
  // 頭2文字より後のローカル部が残っていたら通知に出てしまう
  const local = input.split('@')[0];
  if (input.includes('@') && local.length > 2) assert.ok(!maskEmail(input).includes(local), input);
}
console.log('ok');
