# あいのりごはん 事前登録LP

Cloudflare Pages（Git 連携）で配信。`main` に push すると自動デプロイされる。

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | LP 本体 |
| `privacy.html` | プライバシーポリシー |
| `_worker.js` | 事前登録 API（Pages Functions / D1） |
| `.assetsignore` | 静的配信から除外するパス |

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
