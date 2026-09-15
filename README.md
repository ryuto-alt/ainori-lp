# あいのりごはん 事前登録LP

Cloudflare Pages（Git 連携）で配信。`main` に push すると自動デプロイされる。

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | LP 本体 |
| `privacy.html` | プライバシーポリシー |
| `_worker.js` | 事前登録 API（Pages Functions / D1） |
| `.assetsignore` | 静的配信から除外するパス |

## ルーティング

`_worker.js` が全リクエストを飲み、既定では `env.ASSETS` へ素通しする。自前で返すのは:

| パス | 内容 |
|---|---|
| `/api/register`, `/api/ev` | 事前登録・ファネル計測 |
| `/dash` | ダッシュボード（`DASH_KEY` 未設定なら404） |
| `/.well-known/assetlinks.json` | Android App Links の Digital Asset Links。静的ファイルではなく `_worker.js` の `ASSETLINKS` 定数から返す（先頭ドットのディレクトリは配信経路によって落ちるため） |
| `/i/<招待コード>` | 招待リンクの案内ページ。App Links が効いている端末はここに来る前にアプリが開く。`noindex` |

アプリの署名鍵を作り直した／release 用の鍵を分けたら、`ASSETLINKS` の
`sha256_cert_fingerprints` に**足す**こと（差し替えると旧版アプリのリンクが死ぬ）。

## Cloudflare 設定

- ビルドコマンド・出力ディレクトリともに**空**（ルートをそのまま配信）
- バインディング: D1 `DB` → `ainori-waitlist`
- 環境変数（どちらも Secret）:
  - `DISCORD_WEBHOOK` … 登録通知。任意で、無くても登録は成立する
  - `DASH_KEY` … `/dash?k=` の鍵。**未設定だと /dash は 404**。以前はコードに直書きしていたが、public リポジトリに載るのでやめた

## ローカル

```
npx wrangler pages dev . --d1 DB=ainori-waitlist
```
