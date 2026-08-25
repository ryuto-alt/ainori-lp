/**
 * ainorigohan.com — Cloudflare Pages Advanced Mode worker
 *
 * 静的アセットは env.ASSETS へ素通しし、/api/* と /dash だけ自前で処理する。
 *
 * 経緯(2026-08-11): 事前登録フォームの送信先 /api/register が本番で 405 を返し、
 * 登録が1件も入らない状態だった。デプロイ履歴を辿ると最古の a0404dcb だけが 200 を返し、
 * それ以降の「index.html だけの ZIP 直アップロード」でサーバ側コードが消えていた。
 * プロジェクトのバインディングは残っていたのでコードだけ書き直したもの:
 *   DB              = D1 "ainori-waitlist" / table: waitlist(id, created_at, email, area, user_agent, country)
 *   DISCORD_WEBHOOK = 登録通知(任意。無くても登録は成立する)
 *
 * 追記(2026-08-23): ファネル計測を追加。
 *   /api/ev  … LP から章到達・フォーム入力開始・登録完了を受ける (table: events)
 *   /dash    … 上を集計して出すダッシュボード。?k= に env.DASH_KEY(Secret) が要る。未設定なら404
 *
 * ⚠️ _worker.js は全リクエストを飲み込む。static への素通しを壊すとサイト全体が落ちるので、
 *    既定の分岐は必ず env.ASSETS.fetch(request) のままにすること。
 */

/* 定数で持っていたが、リポジトリを public にした時点で「身内しか見ない」が崩れた。
   コードに書いた鍵は git 履歴からは消せないので、env のシークレットに移して値も変えてある。
   未設定なら 404 で閉じる — 鍵無しで開く方が事故なので、フェイルオープンにはしない。 */

/* 自分とテスト送信。ここを引かないと「登録◯件」が実ユーザー数として読めない。
   実際 8/13 は3件入っていて実ユーザーは0人だった。増えたらここに足す。 */
const NOT_REAL_EMAIL = "(email LIKE '%@example.com' OR email = 'cafiyagi@gmail.com')";

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });

// ponytail: RFC5322 は追わない。形だけ見て、実在確認は配信時に任せる
const EMAIL_RE = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/;

/* ============================================================
   ファネル計測
   ============================================================ */

/* 段。表示順がそのままファネルの順序になる。
   sec:top は view と同時に出るだけなので段に数えない。 */
const STEPS = [
  ['view', 'LP到達'],
  ['sec:yoru', '壱 覚えのある夜'],
  ['sec:tana', '弐 たとえば'],
  ['sec:tsukai', '参 使い方'],
  ['sec:anshin', '肆 安心設計'],
  ['sec:register', '伍 フォーム到達'],
  /* sec:register は「伍章が画面中央線を越えた」だけで、メール欄はまだ画面外にある。
     入力開始までの落差がフォームのせいなのか、そこまで届いていないだけなのかを
     分けるために、メール欄が実際に見えた時点を別の段として取る */
  ['form_view', 'メール欄が見えた'],
  ['form_focus', 'フォーム入力開始'],
  ['lead', '登録完了'],
];

/* PRIMARY KEY(sid,name) で「1セッション1イベント」を DB 側が保証する。
   クライアントの重複抑止が漏れても INSERT OR IGNORE で落ちるだけなので、
   集計側で distinct を書かなくていい。 */
const DDL = `CREATE TABLE IF NOT EXISTS events (
  sid TEXT NOT NULL, name TEXT NOT NULL, ts TEXT NOT NULL,
  src TEXT, country TEXT, device TEXT,
  PRIMARY KEY (sid, name)
)`;

const EV_NAME_RE = /^(view|form_view|form_focus|cta_click|lead|sec:[a-z]{1,24})$/;

async function ensureTable(env) {
  await env.DB.prepare(DDL).run();
}

/* 1イベント書き込み。/api/ev と /api/register の両方から呼ぶ。
   成否だけ返す — 呼び出し側が LP を騒がせるかどうかを決める */
async function recordEvent(request, env, { name, sid, src }) {
  const ua = String(request.headers.get('user-agent') || '');
  const row = [
    sid,
    name,
    new Date().toISOString(),
    String(src || '').slice(0, 60),
    request.headers.get('cf-ipcountry') || '',
    /Mobi|Android|iPhone|iPad/i.test(ua) ? 'mobile' : 'desktop',
  ];
  const INS =
    'INSERT OR IGNORE INTO events (sid, name, ts, src, country, device) VALUES (?, ?, ?, ?, ?, ?)';

  try {
    await env.DB.prepare(INS).bind(...row).run();
  } catch {
    // テーブルが無い初回だけここに落ちる。作ってから一度だけやり直す
    try {
      await ensureTable(env);
      await env.DB.prepare(INS).bind(...row).run();
    } catch {
      return false;
    }
  }
  return true;
}

async function track(request, env) {
  let b;
  try {
    b = await request.json();
  } catch {
    return json({ ok: false }, 400);
  }

  const name = String(b.n || '');
  const sid = String(b.sid || '').slice(0, 40);
  // 名前は集計のキーなので自由文字列を入れさせない。増やすときは STEPS と一緒に足す
  if (!sid || !EV_NAME_RE.test(name)) return json({ ok: false }, 400);

  // 計測の失敗で LP を騒がせない。sendBeacon 側も戻り値を見ていない
  const ok = await recordEvent(request, env, { name, sid, src: b.src });
  return json({ ok }, ok ? 200 : 500);
}

/* ============================================================
   ダッシュボード
   ============================================================ */

const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const pct = (n, d) => (d > 0 ? (n / d) * 100 : 0);
const fmtPct = (n, d) => (d > 0 ? pct(n, d).toFixed(1) + '%' : '—');

async function dash(url, env) {
  const key = env.DASH_KEY;
  if (!key || url.searchParams.get('k') !== key) return new Response('Not found', { status: 404 });

  await ensureTable(env);

  const days = Math.min(Math.max(parseInt(url.searchParams.get('d') || '30', 10) || 30, 1), 365);
  const since = new Date(Date.now() - days * 864e5).toISOString();

  /* 1本コケただけで画面全体が 500 になると、原因を見るための道具が原因を見せずに死ぬ。
     落ちた表は空で描いて、下に注意書きを出す */
  let broke = 0;
  const q = (sql, ...p) =>
    env.DB.prepare(sql)
      .bind(...p)
      .all()
      .then((r) => r.results || [])
      .catch(() => {
        broke++;
        return [];
      });

  const [steps, bySrc, byDev, daily, regs, srcTotals, freeAreas] = await Promise.all([
    q('SELECT name, COUNT(*) n FROM events WHERE ts >= ? GROUP BY name', since),
    q('SELECT src, name, COUNT(*) n FROM events WHERE ts >= ? GROUP BY src, name', since),
    q('SELECT device, name, COUNT(*) n FROM events WHERE ts >= ? GROUP BY device, name', since),
    q(
      "SELECT substr(ts,1,10) d, SUM(name='view') views, SUM(name='lead') leads " +
        'FROM events WHERE ts >= ? GROUP BY d ORDER BY d',
      since
    ),
    q(
      'SELECT substr(created_at,1,10) d, COUNT(*) n, ' +
        `SUM(CASE WHEN ${NOT_REAL_EMAIL} THEN 0 ELSE 1 END) AS "real" ` +
        'FROM waitlist WHERE created_at >= ? GROUP BY d ORDER BY d',
      since
    ),
    q(
      "SELECT src, COUNT(*) n FROM events WHERE ts >= ? AND name='view' GROUP BY src ORDER BY n DESC",
      since
    ),
    /* 「その他」に書かれた地名。期間で切らない — 密度調査は全期間ぶん見たい */
    q(
      `SELECT area_free, COUNT(*) n, MAX(created_at) last FROM waitlist
       WHERE area_free IS NOT NULL AND area_free <> '' AND NOT ${NOT_REAL_EMAIL}
       GROUP BY area_free ORDER BY n DESC, last DESC LIMIT 60`
    ),
  ]);

  const at = (rows, key) => {
    const m = {};
    for (const r of rows) m[key(r)] = (m[key(r)] || 0) + r.n;
    return (k) => m[k] || 0;
  };
  const total = at(steps, (r) => r.name);
  const top = total('view');

  /* --- 段 --- */
  const funnelRows = STEPS.map(([k, label], i) => {
    const n = total(k);
    const prev = i === 0 ? n : total(STEPS[i - 1][0]);
    const drop = prev - n;
    return `<tr>
      <td class="lbl">${esc(label)}</td>
      <td class="barcell"><span class="bar" style="width:${pct(n, top).toFixed(2)}%"></span></td>
      <td class="num">${n}</td>
      <td class="num dim">${fmtPct(n, top)}</td>
      <td class="num ${drop > 0 && prev > 0 && drop / prev > 0.5 ? 'bad' : 'dim'}">${
        /* 章はヘッダーの事前登録CTAで飛ばせる。飛んだ人は前段を通らずに合流するので
           増分になる。ここを「−-7 (-6.5%)」と出すと肆が悪いように読めてしまう */
        i === 0 ? '—' : drop >= 0 ? '−' + drop + ' (' + fmtPct(drop, prev) + ')' : '＋' + -drop + ' 合流'
      }</td>
    </tr>`;
  }).join('');

  /* --- 流入元別 --- */
  const srcRows = srcTotals
    .map((s) => {
      const key = s.src || '';
      const get = at(bySrc.filter((r) => (r.src || '') === key), (r) => r.name);
      return `<tr>
        <td class="lbl">${esc(key || '(direct)')}</td>
        <td class="num">${get('view')}</td>
        <td class="num">${get('sec:register')}</td>
        <td class="num">${get('form_focus')}</td>
        <td class="num strong">${get('lead')}</td>
        <td class="num ${pct(get('lead'), get('view')) >= 5 ? 'good' : 'dim'}">${fmtPct(
        get('lead'),
        get('view')
      )}</td>
      </tr>`;
    })
    .join('');

  /* --- 端末別 --- */
  const devRows = ['mobile', 'desktop']
    .map((d) => {
      const get = at(byDev.filter((r) => r.device === d), (r) => r.name);
      return `<tr>
        <td class="lbl">${d}</td>
        <td class="num">${get('view')}</td>
        <td class="num">${get('sec:register')}</td>
        <td class="num strong">${get('lead')}</td>
        <td class="num ${pct(get('lead'), get('view')) >= 5 ? 'good' : 'dim'}">${fmtPct(
        get('lead'),
        get('view')
      )}</td>
      </tr>`;
    })
    .join('');

  /* --- 日別 --- */
  const regMap = Object.fromEntries(regs.map((r) => [r.d, r]));
  const dayKeys = [...new Set([...daily.map((r) => r.d), ...regs.map((r) => r.d)])].sort();
  const dayMap = Object.fromEntries(daily.map((r) => [r.d, r]));
  const maxV = Math.max(1, ...daily.map((r) => r.views));
  const dailyRows = dayKeys
    .map((d) => {
      const r = dayMap[d] || { views: 0, leads: 0 };
      const g = regMap[d] || { n: 0, real: 0 };
      return `<tr>
        <td class="lbl">${d}</td>
        <td class="barcell"><span class="bar sm" style="width:${pct(r.views, maxV).toFixed(
          2
        )}%"></span></td>
        <td class="num">${r.views}</td>
        <td class="num strong">${g.real}</td>
        <td class="num dim">${g.n - g.real || ''}</td>
        <td class="num dim">${fmtPct(r.leads, r.views)}</td>
      </tr>`;
    })
    .join('');

  const realTotal = regs.reduce((a, r) => a + r.real, 0);
  const rawTotal = regs.reduce((a, r) => a + r.n, 0);

  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="60">
<title>あいのりごはん ファネル</title>
<style>
:root{--bg:#0f0a08;--card:#1a120e;--line:#2e211a;--paper:#f6ecdd;--mute:#a08d7c;--ember:#ff6b2c;--good:#5fd08a;--bad:#e0563a}
*{box-sizing:border-box}
body{margin:0;padding:clamp(16px,4vw,40px);background:var(--bg);color:var(--paper);
  font:15px/1.6 system-ui,-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}
h1{margin:0 0 4px;font-size:1.4rem;letter-spacing:.04em}
h2{margin:34px 0 10px;font-size:.95rem;letter-spacing:.12em;color:var(--mute);font-weight:700}
.sub{color:var(--mute);font-size:.85rem;margin:0 0 18px}
.range a{display:inline-block;margin-right:8px;padding:5px 13px;border:1px solid var(--line);border-radius:999px;
  color:var(--mute);text-decoration:none;font-size:.8rem}
.range a.on{background:var(--ember);border-color:var(--ember);color:#170b05;font-weight:700}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 0}
.kpi{flex:1 1 150px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:1.7rem;line-height:1.2;font-variant-numeric:tabular-nums}
.kpi span{font-size:.75rem;color:var(--mute);letter-spacing:.06em}
.kpi i{font-size:.72rem;opacity:.8}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;min-width:520px}
th,td{padding:9px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:.72rem;letter-spacing:.1em;color:var(--mute);font-weight:600}
tr:last-child td{border-bottom:0}
.num{text-align:right}
.dim{color:var(--mute)}
.strong{color:var(--ember);font-weight:700}
.good{color:var(--good)}
.bad{color:var(--bad)}
.lbl{max-width:260px;overflow:hidden;text-overflow:ellipsis}
.barcell{width:44%;min-width:120px}
.bar{display:block;height:11px;border-radius:999px;background:linear-gradient(90deg,var(--ember),#ff9d5c);min-width:2px}
.bar.sm{height:8px;background:linear-gradient(90deg,#7a5a44,#c98a5e)}
.note{margin-top:26px;color:var(--mute);font-size:.78rem;line-height:1.8}
.note b{color:var(--paper)}
</style></head><body>
<h1>あいのりごはん ファネル</h1>
<p class="sub">直近 ${days} 日 ／ ${new Date().toISOString().replace('T', ' ').slice(0, 16)} UTC 時点</p>
<p class="range">${[1, 7, 30, 90]
    .map(
      (d) =>
        `<a class="${d === days ? 'on' : ''}" href="?k=${encodeURIComponent(key)}&d=${d}">${d}日</a>`
    )
    .join('')}</p>

<div class="kpis">
  <div class="kpi"><b>${top}</b><span>LP到達</span></div>
  <div class="kpi"><b>${total('sec:register')}</b><span>フォーム到達</span></div>
  <div class="kpi"><b>${realTotal}</b><span>実ユーザー登録${
    rawTotal - realTotal ? ` <i>(+自分/テスト ${rawTotal - realTotal})</i>` : ''
  }</span></div>
  <div class="kpi"><b>${fmtPct(total('lead'), top)}</b><span>CVR（計測ベース）</span></div>
</div>

<h2>ファネル</h2>
<div class="wrap"><table>
<tr><th>段</th><th></th><th class="num">人</th><th class="num">対LP</th><th class="num">前段からの離脱</th></tr>
${funnelRows}
</table></div>
<p class="note">うち ${total('cta_click')} 人は事前登録ボタンで章を飛ばしてフォームへ直行した（その分の章は未到達で数えている）。</p>

<h2>「その他」に書かれた場所 <span style="font-weight:400;letter-spacing:0">— 全期間・実ユーザーのみ</span></h2>
<div class="wrap"><table>
<tr><th>場所</th><th></th><th class="num">人</th><th class="num">最終</th></tr>
${
  freeAreas.length
    ? freeAreas
        .map(
          (f) => `<tr>
        <td class="lbl">${esc(f.area_free)}</td>
        <td class="barcell"><span class="bar" style="width:${pct(
          f.n,
          Math.max(1, ...freeAreas.map((x) => x.n))
        ).toFixed(2)}%"></span></td>
        <td class="num strong">${f.n}</td>
        <td class="num dim">${String(f.last).slice(0, 10)}</td>
      </tr>`
        )
        .join('')
    : '<tr><td class="dim" colspan="4">まだ入力がありません</td></tr>'
}
</table></div>

<h2>流入元別</h2>
<div class="wrap"><table>
<tr><th>流入元</th><th class="num">LP</th><th class="num">フォーム到達</th><th class="num">入力開始</th><th class="num">登録</th><th class="num">CVR</th></tr>
${srcRows || '<tr><td class="dim" colspan="6">まだデータがありません</td></tr>'}
</table></div>

<h2>端末別</h2>
<div class="wrap"><table>
<tr><th>端末</th><th class="num">LP</th><th class="num">フォーム到達</th><th class="num">登録</th><th class="num">CVR</th></tr>
${devRows}
</table></div>

<h2>日別</h2>
<div class="wrap"><table>
<tr><th>日</th><th></th><th class="num">LP到達</th><th class="num">実ユーザー</th><th class="num">自分/テスト</th><th class="num">CVR</th></tr>
${dailyRows || '<tr><td class="dim" colspan="6">まだデータがありません</td></tr>'}
</table></div>

${broke ? `<p class="note bad">⚠ ${broke} 本のクエリが失敗した。上の表のどれかは空か不完全。</p>` : ''}
<p class="note">
「人」はセッション単位のユニーク数（1セッションで同じ段は1回だけ数える）。<br>
章の到達判定は、その章が画面の中央線を越えた時点。章はCTAで飛ばせるので、順路ではない。<br>
「伍 フォーム到達」は伍章に入った時点で、メール欄はまだ画面外。実際に入力欄が見えたかは「メール欄が見えた」の段で見る。<br>
「登録完了」は /api/register が保存に成功した時点でサーバー側が記録する（JS切り・離脱でも落ちない）。<br>
<b>数字の出どころが2系統ある。</b><br>
「LP到達」「フォーム到達」「CVR」は、このサイトが自分で撃っている計測イベント（2026-08-23 23:45 JST 開始）。それ以前の流入は入っていない。<br>
「実ユーザー」「自分/テスト」は waitlist テーブルの実レコードで、計測開始前の登録も含む。
実ユーザー = 全レコード − 自分(cafiyagi@gmail.com) − テスト送信(@example.com)。<br>
だから CVR は計測イベント同士（登録完了 ÷ LP到達）で出している。実ユーザー数を計測PVで割ると、
計測開始前の登録が分子に入って 100% を超える。<br>
計測の登録完了が実ユーザーより少ない場合は、計測開始前の登録か、sid を持たずに送信された分。<br>
「その他」の欄は自由入力なので表記ゆれがある（錦糸町 / きんしちょう / 墨田）。
同じ場所が集まってきたら、そこでチップに昇格させる。<br>
このページは60秒ごとに自動で読み直す。
</p>
</body></html>`;

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' },
  });
}

/* ============================================================
   事前登録
   ============================================================ */

/* Discord のチャンネルは本人以外も見るし、スクショも流れる。生のメアドを出す理由が無いので
   ローカル部は頭2文字だけ残す。ドメインは重複や捨てアドの判断に使うので残す。
   元の値は D1 の waitlist にあるので、必要なら /dash から引ける。 */
export const maskEmail = (e) =>
  String(e).replace(/^([^@]{1,2})[^@]*(@.+)$/, (_, head, domain) => `${head}****${domain}`);

/* Discord通知。area は "渋谷,新宿|ref:t.co" の形なので '|' で流入元を切り出す。
   実ユーザーの通し番号を添える — 「今何人目か」を見るためだけに /dash を開くのは無駄なので。 */
async function notify(env, email, area, areaFree) {
  const [where, src] = String(area).split('|');

  let nth = '';
  // 自分やテスト送信では通し番号が動かないので出さない
  if (!/@example\.com$/i.test(email) && email !== 'cafiyagi@gmail.com') {
    try {
      const r = await env.DB.prepare(
        `SELECT COUNT(*) n FROM waitlist WHERE NOT ${NOT_REAL_EMAIL}`
      ).first();
      if (r) nth = ` ── 実ユーザー ${r.n}人目`;
    } catch {
      /* 数えられなくても通知そのものは出す */
    }
  }

  const lines = [
    `🍚 **事前登録${nth}**`,
    `　${maskEmail(email)}`,
    where ? `　${where}` : '',
    areaFree ? `　その他の希望地: **${areaFree}**` : '',
    `　流入元: ${src || '不明（直リンク / アプリ内ブラウザ）'}`,
  ].filter(Boolean);

  const res = await fetch(env.DISCORD_WEBHOOK, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      content: lines.join('\n'),
      // email も area もクライアント由来。"@everyone" を投げられると Webhook が鳴る
      allowed_mentions: { parse: [] },
    }),
  });

  /* Webhook を消された・URLを打ち間違えた場合、ここを黙らせると
     「登録は入っているのに誰も気づかない」状態が延々続く。ログには残す */
  if (!res.ok) console.log('discord webhook failed', res.status, await res.text().catch(() => ''));
  return res;
}

async function register(request, env, ctx) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: 'bad_request' }, 400);
  }

  // ハニーポット。ボットには成功を返して再送させない
  if (String(body.company || '').trim() !== '') return json({ ok: true });

  const email = String(body.email || '').trim().slice(0, 254);
  if (!EMAIL_RE.test(email)) return json({ ok: false, error: 'invalid_email' }, 400);
  // "渋谷|ig/aug/reels_a" 形式。DBに列を足さない方針で流入元を area に相乗りさせているため長め
  const area = String(body.area || '').slice(0, 120);
  /* 「その他」の自由入力。area に相乗りさせると 120字の切り捨てで流入元(|ref:...)が落ちるので別列。
     中身は人が読む前提の自由文字列。改行だけ潰して、正規化は集計時にやる */
  const areaFree = String(body.area_free || '').replace(/\s+/g, ' ').trim().slice(0, 60);

  try {
    await env.DB.prepare(
      'INSERT INTO waitlist (id, created_at, email, area, user_agent, country, area_free) VALUES (?, ?, ?, ?, ?, ?, ?)'
    )
      .bind(
        crypto.randomUUID(),
        new Date().toISOString(),
        email,
        area,
        String(request.headers.get('user-agent') || '').slice(0, 300),
        request.headers.get('cf-ipcountry') || '',
        areaFree
      )
      .run();
  } catch {
    // 保存できていないのに成功を返すと、ユーザーは登録できたつもりで二度と来ない
    return json({ ok: false, error: 'store_failed' }, 500);
  }

  /* 登録完了だけはサーバ側で撃つ。クライアントの sendBeacon は JS 切り/離脱で落ちるので、
     実レコード21件に対して計測の lead が17件しか立たない、という差が出ていた。
     sid はクライアントが持っている計測IDをそのまま送ってもらう。無ければ段としては拾えない */
  const sid = String(body.sid || '').slice(0, 40);
  if (sid) {
    // area 末尾に相乗りしている流入元(|ref:...)を events.src と同じ形に戻す
    const src = area.includes('|') ? area.slice(area.lastIndexOf('|') + 1) : '';
    ctx.waitUntil(recordEvent(request, env, { name: 'lead', sid, src }).catch(() => {}));
  }

  // 通知は落ちても登録は成立。レスポンスを待たせない
  if (env.DISCORD_WEBHOOK) {
    ctx.waitUntil(notify(env, email, area, areaFree).catch(() => {}));
  }

  return json({ ok: true });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/register') {
      if (request.method !== 'POST') return json({ ok: false, error: 'method_not_allowed' }, 405);
      return register(request, env, ctx);
    }

    if (url.pathname === '/api/ev') {
      if (request.method !== 'POST') return json({ ok: false }, 405);
      return track(request, env);
    }

    if (url.pathname === '/dash') return dash(url, env);

    /* Pages の直アップロードは .assetsignore を見ず、ディレクトリを丸ごと上げてしまう。
       test/ と設定ファイルはデプロイ物に混ざるので、配信の手前で落とす。

       2026-08-25: index.html.bak / _worker.js.bak が本番で誰でも落とせる状態になっていて、
       DASH_KEY が平文で読めていた。ローカルから消してデプロイし直しても、
       Pages のアセットストアに残ったままで配信が続く(キャッシュパージでも消えない)。
       残っていても配信されないよう、ここで落とすのが唯一確実な止め方。 */
    if (
      url.pathname.startsWith('/test/') ||
      url.pathname.startsWith('/.wrangler/') ||
      url.pathname.endsWith('.bak') ||
      url.pathname === '/.assetsignore'
    ) {
      return new Response('Not found', { status: 404 });
    }

    return env.ASSETS.fetch(request);
  },
};
